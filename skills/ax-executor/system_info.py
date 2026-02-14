"""
system_info.py - Clean Architecture Refactor

Core responsibilities:
1. Window Detection & App Identity  
2. Accessibility (AX) System
3. Chrome Profile Management
4. App Permissions
5. Event Enrichment (main API)

Eliminates duplication, provides clean interfaces, single source of truth.
"""

import threading
import datetime
import subprocess
import unicodedata
import re
import time
import json
from typing import Optional, Dict, Any, List, Tuple, Set
from pathlib import Path
from dataclasses import dataclass

# macOS Framework Imports
from AppKit import NSWorkspace
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGWindowListExcludeDesktopElements,
)
import pyautogui

# === CORE DATA STRUCTURES ===

@dataclass
class WindowInfo:
    """Standardized window information"""
    title: str
    app: str
    pid: int
    left: int
    top: int
    width: int
    height: int
    layer: int = 0
    alpha: float = 1.0
    bundle: Optional[str] = None

@dataclass
class AXCandidate:
    """Accessibility element candidate"""
    element: Any
    name: str
    role: str
    bounds: Tuple[float, float, float, float]  # x, y, w, h
    enabled: bool
    distance: float
    score: float
    actionable: bool

# === GLOBAL STATE (Minimized) ===

class SystemState:
    """Centralized system state"""
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.last_active_app: Optional[str] = None
        self.last_chrome_profile: Optional[str] = None
        self.app_permissions: Dict[str, bool] = {}
        
    def load_permissions(self):
        """Load app permissions from disk"""
        try:
            perm_file = Path(__file__).parent / "app_permissions.json"
            if perm_file.exists():
                with open(perm_file, 'r') as f:
                    self.app_permissions = json.load(f)
        except Exception:
            pass
    
    def save_permissions(self):
        """Save app permissions to disk"""
        try:
            perm_file = Path(__file__).parent / "app_permissions.json"
            with open(perm_file, 'w') as f:
                json.dump(self.app_permissions, f, indent=2)
        except Exception:
            pass

_state = SystemState()
_state.load_permissions()

# === UTILITY FUNCTIONS ===

def clean_unicode(text: Optional[str]) -> str:
    """Clean unicode text for safe processing"""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', str(text))
    return ''.join(c for c in normalized if ord(c) < 127)

def get_timestamp() -> str:
    """Get standardized timestamp"""
    return datetime.datetime.now().isoformat(timespec='microseconds').replace(":", "-")

# === APP IDENTITY RESOLVER ===

class AppIdentityResolver:
    """Handles app name resolution and process identity"""
    
    @staticmethod
    def extract_from_pid(pid: int) -> Optional[str]:
        """Extract app name from PID (for Electron apps)"""
        try:
            output = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True).strip()
            if "/Applications/" in output:
                return output.split("/Applications/")[1].split(".app")[0]
        except Exception:
            return None

    @staticmethod
    def get_process_name(pid: int) -> Optional[str]:
        """Get clean process name from PID"""
        if not pid or pid <= 0:
            return None
        try:
            result = subprocess.run(['ps', '-p', str(pid), '-o', 'comm='],
                                    capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                proc_name = result.stdout.strip()
                if proc_name:
                    proc_name = proc_name.split('/')[-1].replace('.app', '').split()[0]
                    return proc_name.title() if len(proc_name) > 1 else None
        except Exception:
            pass
        return None

    @staticmethod
    def extract_meaningful_name(text: str) -> Optional[str]:
        """Extract meaningful app name from raw text"""
        if not text:
            return None
        
        # Clean unicode first
        text = clean_unicode(text)
        noise_words = {'the', 'and', 'for', 'new', 'main', 'window', 'document', 'untitled'}
        words = [w.strip() for w in re.split(r'[-–"|()[\]{}]', text)]
        
        for word in words:
            word = word.strip()
            if (len(word) >= 2 and 
                word.lower() not in noise_words and 
                not word.isdigit() and
                not re.match(r'^v?\d+\.\d+', word)):
                return word.title()
        return None

    @classmethod
    def resolve_app_name(cls, raw_app: str, raw_title: str, pid: int) -> str:
        """Single method to resolve app name from all available data"""
        
        # Try cleaned app name first
        if raw_app:
            clean_app = clean_unicode(raw_app)
            if clean_app and '.' in clean_app:
                clean_app = clean_app.split('.')[-1]
            if clean_app and clean_app.lower() not in ['electron', 'helper', 'gpu', 'renderer', 'node', 'main']:
                return clean_app.title()
        
        # Try meaningful name extraction
        for source in [raw_app, raw_title]:
            if source:
                meaningful = cls.extract_meaningful_name(source)
                if meaningful:
                    return meaningful
        
        # Try process name
        proc_name = cls.get_process_name(pid)
        if proc_name:
            return proc_name
            
        # Electron app identity flush
        if raw_app == "Electron" and pid > 0:
            flushed = cls.extract_from_pid(pid)
            if flushed:
                return flushed
                
        return "Unknown"

# === WINDOW DETECTION ENGINE ===

class WindowDetector:
    """Handles window detection and filtering"""
    
    SYSTEM_PROCESSES = {
        "dock", "windowserver", "spotlight", "controlcenter", 
        "notificationcenter", "systemuiserver", "menuextras",
        "loginwindow", "screensaverbg", "desktop"
    }
    
    GOOD_UNNAMED_APPS = {
        "google chrome", "spotify", "finder", "safari", "firefox"
    }
    
    @classmethod
    def get_raw_windows(cls):
        """Get raw window list from system"""
        options = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
        return CGWindowListCopyWindowInfo(options, 0)
    
    @classmethod
    def filter_windows(cls, windows: List[Dict]) -> List[Dict]:
        """Filter out system/problematic windows"""
        filtered = []
        
        for window in windows:
            # Skip invisible windows
            if window.get("kCGWindowAlpha", 1) == 0:
                continue
                
            # Skip system processes
            owner = window.get("kCGWindowOwnerName", "").lower()
            if owner in cls.SYSTEM_PROCESSES:
                continue
                
            # Skip tiny windows
            bounds = window.get("kCGWindowBounds", {})
            if bounds.get("Width", 0) < 10 or bounds.get("Height", 0) < 10:
                continue
                
            # Skip off-screen windows
            if bounds.get("X", 0) < -1000 or bounds.get("Y", 0) < -1000:
                continue
                
            # Skip unnamed windows (except from good apps)
            window_name = window.get("kCGWindowName", "")
            if not window_name or window_name.lower() in ["", "unknown", "window"]:
                if owner not in cls.GOOD_UNNAMED_APPS:
                    continue
            
            filtered.append(window)
            
        return filtered
    
    @classmethod
    def window_dict_to_info(cls, window_dict: Dict) -> WindowInfo:
        """Convert raw window dict to WindowInfo object"""
        bounds = window_dict.get("kCGWindowBounds", {})
        
        app_name = AppIdentityResolver.resolve_app_name(
            window_dict.get("kCGWindowOwnerName", ""),
            window_dict.get("kCGWindowName", ""),
            window_dict.get("kCGWindowOwnerPID", 0)
        )
        
        return WindowInfo(
            title=clean_unicode(window_dict.get("kCGWindowName", "Unknown")),
            app=app_name,
            pid=window_dict.get("kCGWindowOwnerPID", 0),
            left=bounds.get("X", 0),
            top=bounds.get("Y", 0),
            width=bounds.get("Width", 0),
            height=bounds.get("Height", 0),
            layer=window_dict.get("kCGWindowLayer", 0),
            alpha=window_dict.get("kCGWindowAlpha", 1.0)
        )
    
    @classmethod
    def get_window_at_coordinates(cls, x: float, y: float) -> WindowInfo:
        """Get the topmost visible window at coordinates"""
        try:
            windows = cls.get_raw_windows()
            filtered = cls.filter_windows(windows)
            sorted_windows = sorted(filtered, key=lambda w: w.get("kCGWindowLayer", 0), reverse=True)
            
            # Find topmost window containing coordinates
            for window in sorted_windows:
                bounds = window.get("kCGWindowBounds", {})
                wx, wy = bounds.get("X", 0), bounds.get("Y", 0)
                ww, wh = bounds.get("Width", 0), bounds.get("Height", 0)
                
                if wx <= x <= wx + ww and wy <= y <= wy + wh:
                    print(f"🎯 Matched window: {window.get('kCGWindowOwnerName')} | {window.get('kCGWindowName')}")
                    return cls.window_dict_to_info(window)
            
            # Fallback to frontmost app
            return cls.get_frontmost_app_window()
            
        except Exception as e:
            print(f"[⚠️] Window detection error: {e}")
            return cls.get_fallback_window()
    
    @classmethod
    def get_frontmost_app_window(cls) -> WindowInfo:
        """Get frontmost app as window info"""
        try:
            app = NSWorkspace.sharedWorkspace().frontmostApplication()
            return WindowInfo(
                title="Main Window",
                app=clean_unicode(app.localizedName()),
                pid=app.processIdentifier(),
                left=0, top=0,
                width=_state.screen_width,
                height=_state.screen_height,
                bundle=clean_unicode(app.bundleIdentifier() or "")
            )
        except Exception:
            return cls.get_fallback_window()
    
    @classmethod
    def get_fallback_window(cls) -> WindowInfo:
        """Fallback window when detection fails"""
        return WindowInfo(
            title="Desktop",
            app="Finder", 
            pid=0,
            left=0, top=0,
            width=1920, height=1080
        )

# === FRONTMOST APP DETECTOR ===

class FrontmostAppDetector:
    """Handles frontmost app detection"""
    
    @classmethod
    def get_current_app_info(cls) -> WindowInfo:
        """Get current frontmost app using reliable subprocess method"""
        try:
            # Use working subprocess method
            frontmost_app = subprocess.check_output([
                "osascript", "-e", 
                'tell application "System Events" to get name of first application process whose frontmost is true'
            ]).decode().strip()
            
            # Get PID
            try:
                main_pid = subprocess.check_output(["pgrep", "-ix", frontmost_app]).decode().strip().split("\n")[0]
                pid = int(main_pid)
            except Exception:
                pid = -1
            
            # Handle Electron apps
            app_name = frontmost_app
            if app_name == "Electron" and pid > 0:
                flushed = AppIdentityResolver.extract_from_pid(pid)
                if flushed:
                    app_name = flushed
                    print(f"[🔄] Electron flushed to: {flushed}")
            
            _state.last_active_app = app_name
            
            return WindowInfo(
                title="Unknown",
                app=app_name,
                pid=pid,
                left=0, top=0, width=0, height=0
            )
            
        except Exception as e:
            print(f"[⚠️] Error getting current app: {e}")
            return WindowDetector.get_fallback_window()

# === ACCESSIBILITY SYSTEM ===

class AccessibilitySystem:
    """Handles all AX functionality with robust loading"""
    
    def __init__(self):
        self.loaded = False
        self.trusted = False
        self._load_frameworks()
    
    def _load_frameworks(self):
        """Load AX frameworks with fallbacks"""
        self.core_functions = {}
        self.constants = {}
        
        # Try multiple framework sources
        for framework_name in ['ApplicationServices', 'Quartz', 'Accessibility']:
            try:
                framework = __import__(framework_name)
                
                # Core functions
                for func_name in ['AXUIElementCreateApplication', 'AXUIElementCreateSystemWide', 
                                'AXUIElementCopyAttributeValue', 'AXIsProcessTrusted',
                                'AXUIElementCopyElementAtPosition']:
                    if hasattr(framework, func_name) and not self.core_functions.get(func_name):
                        self.core_functions[func_name] = getattr(framework, func_name)
                
                # Constants with CFString fallbacks
                const_map = {
                    'kAXRoleAttribute': 'AXRole',
                    'kAXTitleAttribute': 'AXTitle', 
                    'kAXIdentifierAttribute': 'AXIdentifier',
                    'kAXDescriptionAttribute': 'AXDescription',
                    'kAXPositionAttribute': 'AXPosition',
                    'kAXSizeAttribute': 'AXSize',
                    'kAXChildrenAttribute': 'AXChildren',
                    'kAXParentAttribute': 'AXParent',
                    'kAXEnabledAttribute': 'AXEnabled',
                    'kAXFocusedUIElementAttribute': 'AXFocusedUIElement'
                }
                
                for const_name, fallback in const_map.items():
                    if hasattr(framework, const_name) and not self.constants.get(const_name):
                        self.constants[const_name] = getattr(framework, const_name)
                    elif not self.constants.get(const_name):
                        self.constants[const_name] = fallback
                        
            except ImportError:
                continue
        
        # Check if we have minimum required functions
        required = ['AXUIElementCreateApplication', 'AXUIElementCopyAttributeValue']
        self.loaded = all(self.core_functions.get(func) for func in required)
        
        # Check trust status
        if self.loaded and self.core_functions.get('AXIsProcessTrusted'):
            try:
                self.trusted = bool(self.core_functions['AXIsProcessTrusted']())
            except Exception:
                self.trusted = False
    
    def is_ready(self) -> bool:
        """True if AX is loaded and trusted"""
        return self.loaded and self.trusted
    
    def ax_get(self, element, attribute):
        """Normalized AX attribute getter (handles 2-arg/3-arg variations)"""
        if not self.loaded:
            return -1, None
            
        func = self.core_functions['AXUIElementCopyAttributeValue']
        try:
            result = func(element, attribute)
            if isinstance(result, tuple) and len(result) == 2:
                return result
            return 0, result
        except TypeError:
            try:
                result = func(element, attribute, None)
                if isinstance(result, tuple) and len(result) == 2:
                    return result
                return 0, result
            except Exception:
                return -1, None
    
    def get_element_bounds(self, element) -> Tuple[float, float, float, float]:
        """Get element bounds as (x, y, width, height)"""
        try:
            pos_err, pos_val = self.ax_get(element, self.constants['kAXPositionAttribute'])
            size_err, size_val = self.ax_get(element, self.constants['kAXSizeAttribute'])
            
            if pos_err != 0 or size_err != 0 or not pos_val or not size_val:
                return (0, 0, 0, 0)
            
            # Extract coordinate values (handle different AXValue formats)
            x = getattr(pos_val, 'x', pos_val[0] if hasattr(pos_val, '__getitem__') else 0)
            y = getattr(pos_val, 'y', pos_val[1] if hasattr(pos_val, '__getitem__') else 0)
            w = getattr(size_val, 'width', size_val[0] if hasattr(size_val, '__getitem__') else 0)
            h = getattr(size_val, 'height', size_val[1] if hasattr(size_val, '__getitem__') else 0)
            
            return (float(x), float(y), float(w), float(h))
            
        except Exception:
            return (0, 0, 0, 0)
    
    def get_element_label(self, element) -> str:
        """Get best available label: title → identifier → description → role"""
        try:
            # Try attributes in preference order
            for attr_key in ['kAXTitleAttribute', 'kAXIdentifierAttribute', 'kAXDescriptionAttribute']:
                err, value = self.ax_get(element, self.constants[attr_key])
                if err == 0 and isinstance(value, str) and value.strip():
                    return clean_unicode(value.strip())
            
            # Fallback to role
            err, role = self.ax_get(element, self.constants['kAXRoleAttribute'])
            if err == 0 and isinstance(role, str):
                return role.replace("AX", "").strip() or "Element"
                
            return "Element"
        except Exception:
            return "Element"
    
    def hit_test_neighborhood(self, x: float, y: float, pid: Optional[int] = None) -> List[Any]:
        """Hit-test with neighborhood sampling and element expansion"""
        if not self.is_ready():
            return []
        
        elements = {}  # Deduplicate by element ID
        offsets = [(0, 0), (6, 0), (-6, 0), (0, 6), (0, -6), (6, 6), (-6, -6), (6, -6), (-6, 6)]
        
        for dx, dy in offsets:
            test_x, test_y = x + dx, y + dy
            hit_element = None
            
            # Try app-specific hit-test first
            if pid and pid > 0:
                try:
                    app_elem = self.core_functions['AXUIElementCreateApplication'](pid)
                    if app_elem and self.core_functions.get('AXUIElementCopyElementAtPosition'):
                        result = self.core_functions['AXUIElementCopyElementAtPosition'](app_elem, test_x, test_y)
                        if isinstance(result, tuple) and len(result) == 2:
                            err, hit_element = result
                            if err != 0:
                                hit_element = None
                        else:
                            hit_element = result
                except Exception:
                    pass
            
            # Fallback to system-wide
            if not hit_element and self.core_functions.get('AXUIElementCopyElementAtPosition'):
                try:
                    sys_elem = self.core_functions['AXUIElementCreateSystemWide']()
                    result = self.core_functions['AXUIElementCopyElementAtPosition'](sys_elem, test_x, test_y)
                    if isinstance(result, tuple) and len(result) == 2:
                        err, hit_element = result
                        if err != 0:
                            hit_element = None
                    else:
                        hit_element = result
                except Exception:
                    pass
            
            if hit_element:
                elements[id(hit_element)] = hit_element
                
                # Expand: add parent, siblings, children
                self._expand_element_family(hit_element, elements)
        
        return list(elements.values())
    
    def _expand_element_family(self, element, elements_dict):
        """Add parent, siblings, and children to elements collection"""
        try:
            # Add parent
            parent_err, parent = self.ax_get(element, self.constants['kAXParentAttribute'])
            if parent_err == 0 and parent:
                elements_dict[id(parent)] = parent
                
                # Add siblings (parent's children)
                sibs_err, siblings = self.ax_get(parent, self.constants['kAXChildrenAttribute'])
                if sibs_err == 0 and isinstance(siblings, (list, tuple)):
                    for sib in siblings[:10]:  # Limit siblings
                        if sib:
                            elements_dict[id(sib)] = sib
            
            # Add direct children
            children_err, children = self.ax_get(element, self.constants['kAXChildrenAttribute'])
            if children_err == 0 and isinstance(children, (list, tuple)):
                for child in children[:5]:  # Limit children
                    if child:
                        elements_dict[id(child)] = child
                        
        except Exception:
            pass
    
    def rank_candidates(self, elements: List[Any], x: float, y: float) -> List[AXCandidate]:
        """Rank elements by actionability, distance, and label quality"""
        actionable_roles = {
            "AXButton", "AXCheckBox", "AXPopUpButton", "AXRadioButton", 
            "AXMenuItem", "AXTab", "AXToolbarButton", "AXToggleButton",
            "AXLink", "AXTextField", "AXTextArea", "AXComboBox"
        }
        
        candidates = []
        
        for element in elements:
            try:
                bounds = self.get_element_bounds(element)
                if bounds == (0, 0, 0, 0):
                    continue
                
                label = self.get_element_label(element)
                
                # Get role and enabled status
                role_err, role = self.ax_get(element, self.constants['kAXRoleAttribute'])
                role = role if role_err == 0 and isinstance(role, str) else "Unknown"
                
                enabled_err, enabled = self.ax_get(element, self.constants['kAXEnabledAttribute'])
                is_enabled = enabled if enabled_err == 0 and isinstance(enabled, bool) else True
                
                # Calculate distance to center
                ex, ey, ew, eh = bounds
                center_x, center_y = ex + ew/2, ey + eh/2
                distance = ((x - center_x)**2 + (y - center_y)**2)**0.5
                
                # Scoring
                actionable_score = 100 if role in actionable_roles else 0
                enabled_score = 50 if is_enabled else 0
                label_score = min(len(label) * 2, 50) if label != "Element" else 0
                distance_score = max(0, 100 - distance)
                
                total_score = actionable_score + enabled_score + label_score + distance_score
                
                candidates.append(AXCandidate(
                    element=element,
                    name=label,
                    role=role,
                    bounds=bounds,
                    enabled=is_enabled,
                    distance=distance,
                    score=total_score,
                    actionable=role in actionable_roles
                ))
                
            except Exception:
                continue
        
        return sorted(candidates, key=lambda c: c.score, reverse=True)

# Global AX instance
_ax = AccessibilitySystem()

# === CHROME PROFILE MANAGER ===

class ChromeProfileManager:
    """Handles Chrome profile detection and management"""
    
    @staticmethod
    def get_user_data_dir() -> Path:
        return Path.home() / "Library/Application Support/Google/Chrome"
    
    @classmethod
    def list_profile_dirs(cls) -> Dict[str, Path]:
        """Map profile directory names to their Preferences paths"""
        base = cls.get_user_data_dir()
        profiles = {}
        
        try:
            if not base.exists():
                return profiles
                
            for p in base.iterdir():
                if p.is_dir() and (p.name == "Default" or p.name.lower().startswith("profile ")):
                    pref = p / "Preferences"
                    if pref.exists():
                        profiles[p.name] = pref
        except Exception:
            pass
            
        return profiles
    
    @classmethod
    def get_profile_from_pid(cls, pid: int) -> Optional[str]:
        """Extract --profile-directory from process arguments"""
        try:
            if not pid or pid <= 0:
                return None
            cmd_output = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True)
            if "--profile-directory=" in cmd_output:
                match = re.search(r"--profile-directory=([^\s]+)", cmd_output)
                if match:
                    return match.group(1).strip('"')
        except Exception:
            pass
        return None
    
    @classmethod
    def detect_profile_for_window(cls, window: WindowInfo) -> Optional[str]:
        """Multi-strategy profile detection for Chrome window"""
        if "chrome" not in window.app.lower():
            return None
        
        # Try PID arguments first
        profile = cls.get_profile_from_pid(window.pid)
        if profile:
            _state.last_chrome_profile = profile
            return profile
        
        # Fallback to last known or Default
        return _state.last_chrome_profile or "Default"

# === APP PERMISSIONS MANAGER ===

class AppPermissionsManager:
    """Handles app permission management"""
    
    @classmethod
    def get_allowed_apps(cls) -> Set[str]:
        """Get set of allowed apps for automation"""
        allowed = {app for app, perm in _state.app_permissions.items() if perm}
        
        # Always include essential apps
        essential = {"Finder", "System Preferences", "Terminal"}
        allowed.update(essential)
        
        return allowed
    
    @classmethod
    def is_app_allowed(cls, app_name: str) -> bool:
        """Check if specific app is allowed"""
        return _state.app_permissions.get(app_name, False)
    
    @classmethod
    def update_permissions(cls, permissions: Dict[str, bool]) -> Dict[str, Any]:
        """Update app permissions"""
        _state.app_permissions.update(permissions)
        _state.save_permissions()
        
        return {
            "success": True,
            "updated_count": len(permissions),
            "total_allowed": len([p for p in _state.app_permissions.values() if p])
        }

# === EVENT ENRICHMENT (MAIN API) ===

class EventEnricher:
    """Main API for enriching mouse and keyboard events"""
    
    @classmethod
    def enrich_mouse_event(cls, raw_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Enrich mouse event with window context, relative position, and profiles
        
        Input: {"event": "click", "coordinates": [x, y], "timestamp": "..."}
        Output: Complete enriched event
        """
        try:
            x, y = raw_event["coordinates"]
            window = WindowDetector.get_window_at_coordinates(x, y)
            
            # Filter out recording-controls window
            if "Recording Controls" in window.title:
                return None
            
            # Calculate positions
            rel_x = (x - window.left) / max(window.width, 1)
            rel_y = (y - window.top) / max(window.height, 1)
            norm_x = round(x / _state.screen_width, 4)
            norm_y = round(y / _state.screen_height, 4)
            
            # Chrome profile detection
            chrome_profile = ChromeProfileManager.detect_profile_for_window(window)
            
            return {
                **raw_event,
                "app": window.app,
                "window_title": window.title,
                "app_name": window.app,  # Compatibility
                "chrome_profile": chrome_profile,
                "window": {
                    "title": window.title,
                    "left": window.left,
                    "top": window.top,
                    "width": window.width,
                    "height": window.height
                },
                "rel_position": [round(rel_x, 4), round(rel_y, 4)],
                "position": [norm_x, norm_y],
                "raw_position": [x, y],
                "screen": {
                    "width": _state.screen_width,
                    "height": _state.screen_height
                }
            }
            
        except Exception as e:
            print(f"[⚠️] Error enriching mouse event: {e}")
            return {
                **raw_event,
                "app": "Unknown",
                "window_title": "Unknown",
                "app_name": "Unknown",
                "window": {"title": "Unknown", "left": 0, "top": 0, "width": 0, "height": 0},
                "rel_position": [0.0, 0.0],
                "position": [0.0, 0.0],
                "raw_position": raw_event.get("coordinates", [0, 0]),
                "screen": {"width": _state.screen_width, "height": _state.screen_height}
            }
    
    @classmethod
    def enrich_keyboard_event(cls, raw_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Enrich keyboard event with app context
        
        Input: {"event": "type|key", "text": "hello", "timestamp": "..."}
        Output: Complete enriched event
        """
        try:
            window = FrontmostAppDetector.get_current_app_info()
            
            # Filter out recording-controls window
            if "Recording Controls" in window.title:
                return None
            
            # Chrome profile detection
            chrome_profile = ChromeProfileManager.detect_profile_for_window(window)
            
            return {
                **raw_event,
                "app": window.app,
                "window_title": window.title,
                "app_name": window.app,
                "chrome_profile": chrome_profile,
                "window": {
                    "title": window.title,
                    "left": window.left,
                    "top": window.top,
                    "width": window.width,
                    "height": window.height
                }
            }
            
        except Exception as e:
            print(f"[⚠️] Error enriching keyboard event: {e}")
            return {
                **raw_event,
                "app": "Unknown",
                "window_title": "Unknown",
                "app_name": "Unknown",
                "window": {"title": "Unknown", "left": 0, "top": 0, "width": 0, "height": 0}
            }

# === PUBLIC API (Backward Compatibility) ===

def get_window_at_coordinates(x: float, y: float) -> Dict[str, Any]:
    """Public API: Get window at coordinates (returns dict for compatibility)"""
    window = WindowDetector.get_window_at_coordinates(x, y)
    return {
        "title": window.title,
        "app": window.app,
        "pid": window.pid,
        "left": window.left,
        "top": window.top,
        "width": window.width,
        "height": window.height,
        "layer": window.layer,
        "alpha": window.alpha,
        "bundle": window.bundle
    }

def get_current_app_info() -> Dict[str, Any]:
    """Public API: Get current frontmost app info"""
    window = FrontmostAppDetector.get_current_app_info()
    return {
        "app": window.app,
        "title": window.title,
        "pid": window.pid,
        "left": window.left,
        "top": window.top,
        "width": window.width,
        "height": window.height
    }

def is_accessibility_ready() -> bool:
    """Public API: Check if accessibility is ready"""
    return _ax.is_ready()

def get_elements_near_point(x: float, y: float, radius: int = 24, roles: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Public API: Get AX elements near point - with cascading detection fallbacks"""
    if not _ax.is_ready():
        return []
    
    # Get frontmost app PID and window info for fallbacks
    pid = None
    window_info = None
    try:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app:
            pid = app.processIdentifier()
        # Get window info for heuristics
        from system_info import get_window_at_coordinates
        window_info = get_window_at_coordinates(x, y)
    except Exception:
        pass

    # FOCUS STABILIZATION: Allow focus state to settle
    import time
    time.sleep(0.1)  # 100ms delay for focus to stabilize

    # Define the direct AX function outside the try block
    from ApplicationServices import AXUIElementCopyAttributeValue, kAXFocusedUIElementAttribute

    def _ax_get_direct(el, attr):
        try:
            res = AXUIElementCopyAttributeValue(el, attr)
            if isinstance(res, tuple) and len(res) == 2:
                return res[0], res[1]
            return 0, res
        except TypeError:
            res = AXUIElementCopyAttributeValue(el, attr, None)
            if isinstance(res, tuple) and len(res) == 2:
                return res[0], res[1]
            return 0, res

    # PRIORITY 1: Try focused element detection
    focused_candidates = []
    print(f"[🔍 PID DEBUG] PID found: {pid}")
    if pid:
        try:
            app_elem = _ax.core_functions['AXUIElementCreateApplication'](pid)
            
            # Use direct AX call
            err, focused = _ax_get_direct(app_elem, kAXFocusedUIElementAttribute)
            
            print(f"[🔍 AX RESULT] err={err}, focused={focused is not None}")
            
            if err == 0 and focused:
                label = _ax.get_element_label(focused)
                bounds = _ax.get_element_bounds(focused)
                
                print(f"[🔍 FOCUSED DEBUG] Found focused element with label: '{label}', bounds: {bounds}")
                
                # Only include if it has a meaningful name
                if label and label not in ["Element", "Unknown"]:
                    focused_candidates.append({
                        "element": focused,
                        "name": label,
                        "role": "Focused",
                        "bounds": list(bounds),
                        "enabled": True,
                        "distance": 0,
                        "score": 200,  # High priority score
                        "actionable": True,
                        "detection_method": "accessibility_focused"
                    })
        except Exception as e:
            print(f"[🔍 ERROR] Focused element detection failed: {e}")
            pass

    # PRIORITY 2: Hit-test neighborhood AX detection
    neighborhood_candidates = []
    try:
        elements = _ax.hit_test_neighborhood(x, y, pid)
        candidates = _ax.rank_candidates(elements, x, y)
        
        # Convert neighborhood candidates to dict format
        neighborhood_candidates = [{
            "element": c.element,
            "name": c.name,
            "role": c.role,
            "bounds": list(c.bounds),
            "enabled": c.enabled,
            "distance": c.distance,
            "score": c.score,
            "actionable": c.actionable,
            "detection_method": "accessibility_neighborhood"
        } for c in candidates]
    except Exception as e:
        print(f"[🔍 ERROR] Neighborhood detection failed: {e}")
        pass

    # If AX found meaningful results, return them
    all_ax_candidates = focused_candidates + neighborhood_candidates
    meaningful_ax = [c for c in all_ax_candidates if c["name"] not in ["Element", "Unknown", ""]]

    if meaningful_ax:
        return meaningful_ax

    # PRIORITY 3: Smart Heuristics Fallback
    if window_info:
        try:
            heuristic_name = get_smart_heuristic_name(window_info, x, y)
            if heuristic_name and heuristic_name not in ["Unknown Button", "Unknown Element"]:
                return [{
                    "element": None,
                    "name": heuristic_name,
                    "role": "Heuristic",
                    "bounds": [x-20, y-20, 40, 40],  # Estimated bounds
                    "enabled": True,
                    "distance": 0,
                    "score": 150,
                    "actionable": True,
                    "detection_method": "position_heuristic"
                }]
        except Exception as e:
            print(f"[🔍 ERROR] Heuristics failed: {e}")
            pass

    # PRIORITY 4: OCR Fallback
    try:
        ocr_result = try_ocr_at_coordinates(x, y)
        if ocr_result and len(ocr_result.strip()) > 2:
            return [{
                "element": None,
                "name": clean_unicode(ocr_result.strip()),
                "role": "OCR",
                "bounds": [x-50, y-20, 100, 40],  # Estimated bounds
                "enabled": True,
                "distance": 0,
                "score": 100,
                "actionable": True,
                "detection_method": "ocr"
            }]
    except Exception as e:
        print(f"[🔍 ERROR] OCR failed: {e}")
        pass

    # PRIORITY 5: Generic Fallback
    app_name = window_info.get("app", "Unknown") if window_info else "Unknown"
    return [{
        "element": None,
        "name": f"{app_name} Button",
        "role": "Generic",
        "bounds": [x-25, y-25, 50, 50],
        "enabled": True,
        "distance": 0,
        "score": 50,
        "actionable": True,
        "detection_method": "generic_fallback"
    }]

def get_smart_heuristic_name(window_info: Dict[str, Any], x: float, y: float) -> str:
    """Smart position-based naming using app-specific logic"""
    app_name = window_info.get("app", "").lower()
    
    # Calculate relative position
    left, top = window_info.get("left", 0), window_info.get("top", 0)
    width, height = window_info.get("width", 1), window_info.get("height", 1)
    rel_x = (x - left) / max(width, 1)
    rel_y = (y - top) / max(height, 1)
    
    # App-specific heuristics
    if "whatsapp" in app_name or "telegram" in app_name:
        if rel_y > 0.8:
            return "Send Message"
        elif rel_x < 0.2:
            return "Chat List"
        elif rel_y < 0.2:
            return "Search Contacts"
        else:
            return "Chat Element"
            
    elif "excel" in app_name or "word" in app_name:
        if rel_y < 0.3:  # Ribbon area
            if rel_x < 0.3:
                return "File Menu"
            elif rel_x < 0.6:
                return "Home Ribbon"
            else:
                return "Ribbon Tool"
        else:
            return "Document Element"
            
    elif "chrome" in app_name or "firefox" in app_name or "safari" in app_name:
        if rel_y < 0.15:  # Browser top bar
            if rel_x > 0.8:
                return "Menu Button"
            elif rel_x > 0.7:
                return "Extension"
            else:
                return "Browser Control"
        else:
            return "Web Element"
            
    elif "code" in app_name or "vscode" in app_name:
        if rel_x < 0.1:
            return "Sidebar Tool"
        elif rel_y < 0.1:
            return "Menu Item"
        else:
            return "Editor Element"
            
    elif "slack" in app_name:
        if rel_x < 0.25:
            return "Channel List"
        elif rel_y > 0.85:
            return "Message Input"
        else:
            return "Message Element"
            
    elif "discord" in app_name:
        if rel_x < 0.2:
            return "Server List"
        elif rel_x < 0.4:
            return "Channel List"
        elif rel_y > 0.85:
            return "Message Input"
        else:
            return "Chat Element"
            
    elif "figma" in app_name:
        if rel_x > 0.8:
            return "Properties Panel"
        elif rel_x < 0.1:
            return "Tools Panel"
        elif rel_y < 0.1:
            return "Menu Bar"
        else:
            return "Canvas Element"
            
    elif "notion" in app_name:
        if rel_x < 0.25:
            return "Sidebar Item"
        elif rel_y < 0.1:
            return "Page Title"
        else:
            return "Content Block"

    # Generic position-based naming
    if rel_y < 0.2:
        return "Header Element"
    elif rel_y > 0.8:
        return "Footer Element"
    elif rel_x < 0.2:
        return "Sidebar Element"
    elif rel_x > 0.8:
        return "Panel Element"
    else:
        return "Main Element"

def try_ocr_at_coordinates(x: float, y: float) -> Optional[str]:
    """OCR fallback using existing screenshot infrastructure"""
    try:
        from screenshot_taker import take_cropped_screenshot
        from run_ocr_mac_native import run_ocr_mac_native
        from pathlib import Path
        
        # Take screenshot crop around coordinates
        crop_path = take_cropped_screenshot(
            center_x=int(x), 
            center_y=int(y), 
            crop_size=120,  # Slightly larger for button text
            folder=str(Path(__file__).parent / "temp_ocr")
        )
        
        # Run OCR
        ocr_result = run_ocr_mac_native(crop_path)
        
        if ocr_result and ocr_result.get("reconstructed_text"):
            raw_text = ocr_result["reconstructed_text"]
            # Clean and normalize text
            clean_text = " ".join(raw_text.replace("\n", " ").split())
            # Return first meaningful chunk (likely button text)
            if len(clean_text.strip()) > 2:
                return clean_text.strip()[:50]  # Limit length
                
        return None
        
    except Exception:
        return None

def get_element_name(element) -> str:
    """Public API: Get name/label for AX element"""
    if not element:
        return ""
    return _ax.get_element_label(element)

def enrich_mouse_event(raw_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Public API: Enrich mouse event"""
    return EventEnricher.enrich_mouse_event(raw_event)

def enrich_keyboard_event(raw_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Public API: Enrich keyboard event"""
    return EventEnricher.enrich_keyboard_event(raw_event)

# === LEGACY COMPATIBILITY ===

def resolve_active_app_event(source: str, coordinates=None, key_event=None) -> Optional[Dict[str, Any]]:
    """Legacy function for backward compatibility"""
    if source == "mouse" and coordinates:
        x, y = coordinates
        raw_event = {
            "event": "click",
            "coordinates": [x, y],
            "timestamp": get_timestamp()
        }
        return enrich_mouse_event(raw_event)
    else:
        raw_event = {
            "event": "key",
            "timestamp": get_timestamp()
        }
        return enrich_keyboard_event(raw_event)

def calculate_replay_click(recorded_click: dict, target_window: dict) -> Tuple[int, int]:
    """Calculate replay coordinates from recorded click and target window"""
    if not isinstance(recorded_click, dict) or "rel_position" not in recorded_click:
        raise ValueError("Missing 'rel_position' in recorded_click")

    if not isinstance(target_window, dict):
        raise ValueError("target_window must be a dictionary")

    if any(k not in target_window for k in ["left", "top", "width", "height"]):
        raise ValueError("target_window missing required keys")

    rel_x, rel_y = recorded_click["rel_position"]
    new_x = target_window["left"] + (rel_x * target_window["width"])
    new_y = target_window["top"] + (rel_y * target_window["height"])

    return round(new_x), round(new_y)

# === APP PERMISSIONS PUBLIC API ===

def get_allowed_apps() -> Set[str]:
    """Public API: Get allowed apps for automation"""
    return AppPermissionsManager.get_allowed_apps()

def is_app_allowed(app_name: str) -> bool:
    """Public API: Check if app is allowed"""
    return AppPermissionsManager.is_app_allowed(app_name)

def update_app_permissions(permissions: Dict[str, bool]) -> Dict[str, Any]:
    """Public API: Update app permissions"""
    return AppPermissionsManager.update_permissions(permissions)

def discover_installed_apps() -> List[Dict[str, str]]:
    """Public API: Discover installed applications"""
    apps = []
    
    try:
        # Get apps from /Applications
        apps_dir = Path("/Applications")
        for app_path in apps_dir.glob("*.app"):
            apps.append({
                "name": app_path.stem,
                "path": str(app_path),
                "source": "system"
            })
        
        # Get running apps
        workspace = NSWorkspace.sharedWorkspace()
        for app in workspace.runningApplications():
            app_name = app.localizedName()
            if app_name and app_name not in [a["name"] for a in apps]:
                apps.append({
                    "name": app_name,
                    "path": app.bundleURL().path() if app.bundleURL() else "",
                    "source": "running"
                })
                
    except Exception as e:
        print(f"[⚠️] Error discovering apps: {e}")
    
    return sorted(apps, key=lambda x: x["name"])

def discover_automation_apps() -> Set[str]:
    """Public API: Discover apps used in existing automations"""
    automation_apps = set()
    
    try:
        codex_dir = Path(__file__).parent / "codex"
        if codex_dir.exists():
            for json_file in codex_dir.glob("**/*.json"):
                try:
                    with open(json_file, 'r') as f:
                        automation = json.load(f)
                    
                    if not isinstance(automation, dict):
                        continue
                        
                    # Extract apps from steps
                    for step in automation.get("steps", []):
                        if isinstance(step, dict):
                            app = step.get("app")
                            if app and app != "Unknown":
                                cleaned = clean_unicode(app)
                                if cleaned:
                                    automation_apps.add(cleaned)
                    
                    # Extract from settings
                    settings = automation.get("settings", {})
                    if isinstance(settings, dict):
                        target_apps = settings.get("target_apps", [])
                        if isinstance(target_apps, list):
                            for app in target_apps:
                                cleaned = clean_unicode(app)
                                if cleaned:
                                    automation_apps.add(cleaned)
                                    
                except Exception as e:
                    print(f"[⚠️] Error reading {json_file}: {e}")
                    
    except Exception as e:
        print(f"[⚠️] Error scanning automations: {e}")
        
    return automation_apps

def get_app_permission_status() -> Dict[str, Any]:
    """Public API: Get comprehensive app permission status"""
    installed = discover_installed_apps()
    automation = discover_automation_apps()
    
    categorized = {
        "automation_required": [],
        "system_installed": [],
        "currently_allowed": [],
        "suggested": []
    }
    
    # Apps required by automations
    for app_name in automation:
        categorized["automation_required"].append({
            "name": app_name,
            "allowed": _state.app_permissions.get(app_name, False),
            "required": True,
            "installed": any(a["name"] == app_name for a in installed)
        })
    
    # All installed apps
    for app in installed:
        if app["name"] not in automation:
            categorized["system_installed"].append({
                "name": app["name"],
                "allowed": _state.app_permissions.get(app["name"], False),
                "required": False,
                "installed": True,
                "path": app["path"]
            })
    
    # Currently allowed
    for app_name, allowed in _state.app_permissions.items():
        if allowed:
            categorized["currently_allowed"].append(app_name)
    
    # Suggestions
    common_apps = {
        "Google Chrome", "Chrome", "Safari", "Firefox",
        "Slack", "WhatsApp", "Telegram", "Discord", 
        "Spotify", "Music", "Terminal", "VS Code", "Claude"
    }
    
    for app in installed:
        if (app["name"] in common_apps and 
            app["name"] not in automation and
            not _state.app_permissions.get(app["name"], False)):
            categorized["suggested"].append({
                "name": app["name"],
                "reason": "Commonly automated app",
                "installed": True
            })
    
    return categorized

def auto_allow_automation_apps() -> int:
    """Public API: Auto-allow apps used in automations"""
    automation_apps = discover_automation_apps()
    count = 0
    
    for app_name in automation_apps:
        if not _state.app_permissions.get(app_name, False):
            _state.app_permissions[app_name] = True
            count += 1
    
    if count > 0:
        _state.save_permissions()
        print(f"[🤖] Auto-allowed {count} automation apps")
    
    return count

# === CHROME PROFILE PUBLIC API ===

def chrome_profile_for_pid(pid: int) -> Optional[str]:
    """Public API: Get Chrome profile for PID"""
    return ChromeProfileManager.get_profile_from_pid(pid)

def get_active_chrome_profiles() -> List[str]:
    """Public API: List active Chrome profiles"""
    profiles = set()
    try:
        proc = subprocess.run(["ps", "-ax", "-o", "command="], capture_output=True, text=True)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if "--profile-directory=" in line:
                    match = re.search(r"--profile-directory=([^\s]+)", line)
                    if match:
                        profiles.add(match.group(1).strip('"'))
    except Exception:
        pass
    return sorted(profiles)

def get_active_chrome_profile() -> str:
    """Public API: Get active Chrome profile (legacy compatibility)"""
    # Try to read Chrome Local State for last used profile
    try:
        local_state_path = Path.home() / "Library/Application Support/Google/Chrome/Local State"
        if local_state_path.exists():
            with open(local_state_path, "r") as f:
                data = json.load(f)
            return data.get("profile", {}).get("last_used", "Default")
    except Exception:
        pass
    return "Default"

def get_chrome_profile_info(pid: int) -> str:
    """Public API: Legacy Chrome profile detection"""
    profile = ChromeProfileManager.get_profile_from_pid(pid)
    return profile if profile else "Default"

def detect_chrome_profile_for_window(window: Dict[str, Any]) -> Optional[str]:
    """Public API: Detect Chrome profile for window dict"""
    window_info = WindowInfo(
        title=window.get("title", ""),
        app=window.get("app", ""),
        pid=window.get("pid", 0),
        left=window.get("left", 0),
        top=window.get("top", 0),
        width=window.get("width", 0),
        height=window.get("height", 0)
    )
    return ChromeProfileManager.detect_profile_for_window(window_info)

def resolve_chrome_profile_directory(name_or_dir: str) -> str:
    """Public API: Resolve Chrome profile name to directory"""
    if not name_or_dir:
        return "Default"
    
    candidate = str(name_or_dir).strip().strip('"')
    
    if candidate.lower().startswith("profile ") or candidate.lower() == "default":
        return candidate
    
    # Try to read Chrome Local State for profile mapping
    try:
        local_state_path = Path.home() / "Library/Application Support/Google/Chrome/Local State"
        if local_state_path.exists():
            with open(local_state_path, "r") as f:
                data = json.load(f)
            
            cache = data.get("profile", {}).get("info_cache", {})
            for directory_id, meta in cache.items():
                visible = meta.get("name", "")
                if visible.strip().lower() == candidate.lower():
                    return directory_id
            
            # Fallback to last_used
            last_used = data.get("profile", {}).get("last_used")
            if last_used:
                return last_used
                
    except Exception:
        pass
    
    return "Default"

def open_chrome_with_profile(profile: str, urls: Optional[List[str]] = None,
                           force_new_instance: bool = True, new_window: bool = True,
                           wait_seconds: float = 0.0) -> Dict[str, Any]:
    """Public API: Launch Chrome with specific profile"""
    try:
        profile_dir = resolve_chrome_profile_directory(profile)
        
        base = ["open", "-na" if force_new_instance else "-a", "Google Chrome"]
        args = ["--args", f"--profile-directory={profile_dir}"]
        if new_window:
            args.append("--new-window")
        
        cmd = base + args
        if urls:
            cmd.extend(urls)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        
        if result.returncode == 0:
            return {"success": True, "cmd": cmd, "profile_dir": profile_dir}
        else:
            return {
                "success": False,
                "cmd": cmd,
                "profile_dir": profile_dir,
                "error": result.stderr or result.stdout or "Chrome launch failed"
            }
            
    except Exception as e:
        return {"success": False, "cmd": [], "profile_dir": str(profile), "error": str(e)}

# === UTILITY PUBLIC API ===

def debug_windows_at_coordinates(x: float, y: float):
    """Public API: Debug window detection"""
    windows = WindowDetector.get_raw_windows()
    print(f"\n🎯 Windows at coordinates ({x}, {y}):")
    
    for i, window in enumerate(windows):
        bounds = window.get("kCGWindowBounds", {})
        wx, wy = bounds.get("X", 0), bounds.get("Y", 0)
        ww, wh = bounds.get("Width", 0), bounds.get("Height", 0)
        
        if wx <= x <= wx + ww and wy <= y <= wy + wh:
            print(f"  {i}: {window.get('kCGWindowOwnerName')} - {window.get('kCGWindowName')}")
            print(f"     Layer: {window.get('kCGWindowLayer')}, Alpha: {window.get('kCGWindowAlpha')}")
            print(f"     Bounds: ({wx}, {wy}, {ww}, {wh})")

# === INITIALIZATION ===

def start_app_activation_listener():
    """Start listening for app activation events (legacy compatibility)"""
    # Modern implementation using NSWorkspace notifications
    def monitor_app_changes():
        try:
            workspace = NSWorkspace.sharedWorkspace()
            # Note: In the refactor, we rely on real-time detection instead of persistent listeners
            # This maintains API compatibility while using a more reliable approach
            pass
        except Exception:
            pass
    
    # Start as daemon thread for compatibility
    thread = threading.Thread(target=monitor_app_changes, daemon=True)
    thread.start()

def get_last_active_app() -> Optional[str]:
    """Get last active app name (legacy compatibility)"""
    return _state.last_active_app

# Auto-start listener for compatibility
start_app_activation_listener()

# === DEBUG UTILITIES ===

def debug_ax_status():
    """Debug AX system status"""
    print(f"[🔍 AX DEBUG] Loaded: {_ax.loaded}")
    print(f"[🔍 AX DEBUG] Trusted: {_ax.trusted}")
    print(f"[🔍 AX DEBUG] Ready: {_ax.is_ready()}")
    print(f"[🔍 AX DEBUG] Core functions: {list(_ax.core_functions.keys())}")

# === EXPORTS ===

__all__ = [
    # Core event enrichment API
    "enrich_mouse_event",
    "enrich_keyboard_event",
    
    # Window and app detection
    "get_window_at_coordinates", 
    "get_current_app_info",
    
    # Accessibility
    "is_accessibility_ready",
    "get_elements_near_point",
    "get_element_name",
    
    # Utilities
    "clean_unicode",
    "get_timestamp",
    "calculate_replay_click",
    "debug_windows_at_coordinates",
    
    # App permissions
    "get_allowed_apps",
    "is_app_allowed", 
    "update_app_permissions",
    "discover_installed_apps",
    "discover_automation_apps",
    "get_app_permission_status",
    "auto_allow_automation_apps",
    
    # Chrome profiles
    "chrome_profile_for_pid",
    "get_active_chrome_profiles",
    "get_active_chrome_profile",  # Added missing function
    "get_chrome_profile_info",    # Added missing function
    "detect_chrome_profile_for_window",
    "resolve_chrome_profile_directory",
    "open_chrome_with_profile",
    
    # Legacy compatibility
    "resolve_active_app_event",
    "start_app_activation_listener", 
    "get_last_active_app"
]
