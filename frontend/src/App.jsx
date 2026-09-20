import { useEffect, useRef, useState, Component } from "react";
import {
  LayoutDashboard,
  FileText,
  Upload,
  ShieldAlert,
  ListChecks,
  MessageSquare,
  BarChart3,
  Settings,
  Search,
  Bell,
  ChevronDown,
  Menu,
  X,
  Link,
  Image,
  Mic,
  Video,
  CheckCircle2,
  Trash2,
  ArrowLeft,
  Sparkles,
  FileUp,
  Loader2,
  AlertCircle,
  Users,
  CalendarDays,
  DollarSign,
  Bot,
  Send,
  Network,
  ArrowRight,
  CornerDownRight,
  GitFork,
  ShieldCheck,
  KeyRound,
  Sliders,
  LogOut,
  RefreshCw,
  Printer,
  Download,
  TrendingUp,
  Clock,
  Share2,
  User,
  Camera,
  HelpCircle,
  Info,
  ChevronRight,
} from "lucide-react";

import {
  ingestContractUrl,
  uploadContractAudio,
  uploadContractFile,
  uploadContractVideo,
} from "./api/ingestionApi";
import {
  getContractAnalysis,
  getContractSummary,
  getContractRelationships,
} from "./api/analysisApi";
import { askContractQuestion, getQAHistory } from "./api/qaApi";
import { getCurrentUser, exchangeOAuthCode } from "./api/authApi";
import { getContracts, deleteContract } from "./api/contractsApi";
import Login from "./components/Login";
import Register from "./components/Register";
import SplashScreen from "./components/SplashScreen";

import "./App.css";

const navigation = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "contracts", label: "Contracts", icon: FileText },
  { id: "upload", label: "Upload Contract", icon: Upload },
  { id: "analysis", label: "Risk Analysis", icon: ShieldAlert },
  { id: "clauses", label: "Clause Explorer", icon: ListChecks },
  { id: "reports", label: "Reports", icon: BarChart3 },
];

const acceptedFileTypes = [
  ".pdf",
  ".doc",
  ".docx",
  ".txt",
  ".png",
  ".jpg",
  ".jpeg",
  ".wav",
  ".mp3",
  ".ogg",
  ".mp4",
  ".mov",
  ".avi",
];

// Module-scoped in-flight exchange promise to deduplicate execution across React 18 StrictMode double-mounting
let inFlightOAuthExchange = null;

function formatContractDate(dateStr) {
  if (!dateStr) return "Unknown date";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "Unknown date";
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "Unknown date";
  }
}

function formatNotificationTime(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    const now = new Date();
    const diffMs = now - d;
    if (diffMs < 0) return "Just now";
    const diffMins = Math.floor(diffMs / (1000 * 60));
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  } catch {
    return "";
  }
}

function App() {
  const [showSplash, setShowSplash] = useState(() => {
    // If returning from an OAuth callback with an exchange code or error, bypass splash screen
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.has("oauth_code") || params.has("error")) {
        return false;
      }
    }
    return true;
  });
  const [activePage, setActivePage] = useState("dashboard");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [authState, setAuthState] = useState("checking");
  const [authScreen, setAuthScreen] = useState("login");

  const [currentFileId, setCurrentFileId] = useState(null);
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [contracts, setContracts] = useState([]);
  const [contractsLoading, setContractsLoading] = useState(false);
  const [contractsError, setContractsError] = useState("");
  const [selectedAnalysisLoading, setSelectedAnalysisLoading] = useState(false);
  const [selectedAnalysisError, setSelectedAnalysisError] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const [userLoading, setUserLoading] = useState(false);

  // Global search state
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchSelectedIndex, setSearchSelectedIndex] = useState(-1);
  const searchContainerRef = useRef(null);
  const searchInputRef = useRef(null);

  // Notifications state
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const notificationsRef = useRef(null);
  const [readNotificationIds, setReadNotificationIds] = useState(() => {
    try {
      const saved = localStorage.getItem("termShield_read_notifications");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Profile customization override state (stored in localStorage)
  const [profileOverride, setProfileOverride] = useState(() => {
    try {
      const saved = localStorage.getItem("termShield_profile_override");
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  // Profile dropdown menu state
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const profileDropdownRef = useRef(null);

  // Active modal state: null | "editProfile" | "help" | "about"
  const [activeModal, setActiveModal] = useState(null);

  const fetchCurrentUser = async () => {
    setUserLoading(true);
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
      return user;
    } catch (err) {
      setCurrentUser(null);
      throw err;
    } finally {
      setUserLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    // Check for OAuth callback exchange code or error in URL query
    const urlParams = new URLSearchParams(window.location.search);
    const oauthCode = urlParams.get("oauth_code");
    const errorFromUrl = urlParams.get("error");

    if (errorFromUrl) {
      window.history.replaceState({}, document.title, window.location.pathname);
      setAuthScreen("login");
      setAuthState("unauthenticated");
      return () => {
        cancelled = true;
      };
    }

    // Handle OAuth single-use code exchange with deduping across StrictMode remounts
    if (oauthCode || inFlightOAuthExchange) {
      setUserLoading(true);

      if (!inFlightOAuthExchange && oauthCode) {
        inFlightOAuthExchange = exchangeOAuthCode(oauthCode)
          .then((response) => {
            if (response?.access_token) {
              localStorage.setItem("termShieldToken", response.access_token);
              // Clean up the URL query only AFTER successful token storage
              window.history.replaceState({}, document.title, window.location.pathname);
              return response;
            }
            throw new Error("The exchange response did not include an access token.");
          })
          .catch((err) => {
            localStorage.removeItem("termShieldToken");
            window.history.replaceState({}, document.title, window.location.pathname);
            throw err;
          })
          .finally(() => {
            // Allow future exchanges after a short interval
            setTimeout(() => {
              inFlightOAuthExchange = null;
            }, 1000);
          });
      }

      inFlightOAuthExchange
        .then((response) => {
          if (!cancelled && response?.user) {
            setCurrentUser(response.user);
            setAuthState("authenticated");
          }
        })
        .catch(() => {
          if (!cancelled) {
            setCurrentUser(null);
            setAuthScreen("login");
            setAuthState("unauthenticated");
          }
        })
        .finally(() => {
          if (!cancelled) {
            setUserLoading(false);
          }
        });

      return () => {
        cancelled = true;
      };
    }

    const token = localStorage.getItem("termShieldToken");

    if (!token) {
      setAuthScreen("login");
      setAuthState("unauthenticated");
      return () => {
        cancelled = true;
      };
    }

    setUserLoading(true);
    getCurrentUser()
      .then((user) => {
        if (!cancelled) {
          setCurrentUser(user);
          setAuthState("authenticated");
        }
      })
      .catch(() => {
        localStorage.removeItem("termShieldToken");
        if (!cancelled) {
          setCurrentUser(null);
          setAuthScreen("login");
          setAuthState("unauthenticated");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setUserLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const refreshContracts = async () => {
    setContractsLoading(true);
    setContractsError("");

    try {
      const data = await getContracts();
      setContracts(Array.isArray(data) ? data : []);
    } catch (error) {
      setContractsError(
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        "Unable to load your contract library."
      );
    } finally {
      setContractsLoading(false);
    }
  };

  useEffect(() => {
    if (authState !== "authenticated") return undefined;

    refreshContracts();
  }, [authState]);

  const activeItem = navigation.find((item) => item.id === activePage);

  const handleLoginSuccess = () => {
    setAuthState("authenticated");
    fetchCurrentUser().catch(() => { });
  };

  const handleRegisterSuccess = () => {
    setAuthState("authenticated");
    fetchCurrentUser().catch(() => { });
  };

  const handleLogout = () => {
    localStorage.removeItem("termShieldToken");
    setCurrentUser(null);
    setCurrentFileId(null);
    setCurrentAnalysis(null);
    setSelectedAnalysisLoading(false);
    setSelectedAnalysisError("");
    setContracts([]);
    setContractsError("");
    setActivePage("dashboard");
    setAuthScreen("login");
    setAuthState("unauthenticated");
    setSearchQuery("");
    setIsSearchOpen(false);
    setSearchSelectedIndex(-1);
    setIsNotificationsOpen(false);
    setIsProfileDropdownOpen(false);
    setActiveModal(null);
  };

  const handleNavigation = (id) => {
    setActivePage(id);
    setMobileMenu(false);
  };

  const handleContractSelect = async (selectedContractId) => {
    setCurrentFileId(selectedContractId);
    setCurrentAnalysis(null);
    setSelectedAnalysisLoading(true);
    setSelectedAnalysisError("");
    setActivePage("analysis");

    try {
      const analysis = await getContractAnalysis(selectedContractId);
      setCurrentAnalysis(analysis);
    } catch (error) {
      setSelectedAnalysisError(
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        "Unable to load the selected contract analysis."
      );
    } finally {
      setSelectedAnalysisLoading(false);
    }
  };

  const handleDeleteContract = async (contractId) => {
    await deleteContract(contractId);
    if (currentFileId === contractId) {
      setCurrentFileId(null);
      setCurrentAnalysis(null);
      setSelectedAnalysisLoading(false);
      setSelectedAnalysisError("");
    }
    await refreshContracts();
  };

  // Close dropdowns on outside click or Escape key, focus search on Cmd/Ctrl+K
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        searchContainerRef.current &&
        !searchContainerRef.current.contains(event.target)
      ) {
        setIsSearchOpen(false);
      }
      if (
        notificationsRef.current &&
        !notificationsRef.current.contains(event.target)
      ) {
        setIsNotificationsOpen(false);
      }
      if (
        profileDropdownRef.current &&
        !profileDropdownRef.current.contains(event.target)
      ) {
        setIsProfileDropdownOpen(false);
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsSearchOpen(false);
        setIsNotificationsOpen(false);
        setIsProfileDropdownOpen(false);
        setActiveModal(null);
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
        if (searchQuery.trim()) {
          setIsSearchOpen(true);
        }
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [searchQuery]);

  // Global search filtering against user contracts (case-insensitive partial match)
  const filteredContracts = contracts.filter((c) => {
    if (!searchQuery.trim()) return false;
    const q = searchQuery.trim().toLowerCase();
    const filename = String(c?.filename || "").toLowerCase();
    const name = String(c?.name || "").toLowerCase();
    const title = String(c?.title || "").toLowerCase();
    return filename.includes(q) || name.includes(q) || title.includes(q);
  });

  const handleSearchKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setIsSearchOpen(true);
      setSearchSelectedIndex((prev) =>
        prev < filteredContracts.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setIsSearchOpen(true);
      setSearchSelectedIndex((prev) =>
        prev > 0 ? prev - 1 : filteredContracts.length - 1
      );
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (
        searchSelectedIndex >= 0 &&
        searchSelectedIndex < filteredContracts.length
      ) {
        const target = filteredContracts[searchSelectedIndex];
        handleContractSelect(target.id);
        setIsSearchOpen(false);
        setSearchSelectedIndex(-1);
      } else if (filteredContracts.length > 0) {
        handleContractSelect(filteredContracts[0].id);
        setIsSearchOpen(false);
        setSearchSelectedIndex(-1);
      }
    } else if (e.key === "Escape") {
      setIsSearchOpen(false);
      setSearchSelectedIndex(-1);
    }
  };

  // Generate meaningful application notifications from real contract & risk data
  const notifications = (() => {
    if (!Array.isArray(contracts) || contracts.length === 0) return [];
    const list = [];

    contracts.forEach((c) => {
      const contractId = c.id;
      const filename = c.filename || c.name || "Contract";
      const risk = String(c.overall_risk || "").toLowerCase();
      const score = typeof c.overall_risk_score === "number" ? c.overall_risk_score : null;
      const status = String(c.status || "").toLowerCase();
      const createdAt = c.created_at || null;

      // High-risk contract alert
      if (risk === "high" || (score !== null && score >= 70)) {
        list.push({
          id: `high_risk_${contractId}`,
          contractId,
          type: "high_risk",
          title: "High-risk contract detected",
          message: `"${filename}" flagged with high-risk clauses (Score: ${score !== null ? `${score}/100` : "High"}). Requires immediate review.`,
          date: createdAt,
          priority: 1,
        });
      }
      // Medium-risk review notification
      else if (risk === "medium" || risk === "med" || (score !== null && score >= 40 && score < 70)) {
        list.push({
          id: `med_risk_${contractId}`,
          contractId,
          type: "medium_risk",
          title: "Medium-risk contract requires review",
          message: `"${filename}" contains clauses flagged for moderate scrutiny.`,
          date: createdAt,
          priority: 2,
        });
      }

      // Analysis completed notification
      if (status === "analyzed" || status === "ready" || risk || score !== null) {
        list.push({
          id: `analysis_ready_${contractId}`,
          contractId,
          type: "completed",
          title: "Contract analysis completed",
          message: `Intelligence summary and clause risk breakdown are ready for "${filename}".`,
          date: createdAt,
          priority: 3,
        });
      }

      // New contract added notification
      list.push({
        id: `new_contract_${contractId}`,
        contractId,
        type: "added",
        title: "New contract added",
        message: `"${filename}" was uploaded and added to your workspace library.`,
        date: createdAt,
        priority: 4,
      });
    });

    // Prioritize high-risk alerts first, then newest chronologically
    return list
      .sort((a, b) => {
        if (a.priority !== b.priority) {
          return a.priority - b.priority;
        }
        const timeA = a.date ? new Date(a.date).getTime() : 0;
        const timeB = b.date ? new Date(b.date).getTime() : 0;
        return timeB - timeA;
      })
      .slice(0, 15);
  })();

  const unreadCount = notifications.filter(
    (n) => !readNotificationIds.includes(n.id)
  ).length;

  const markNotificationAsRead = (id) => {
    setReadNotificationIds((prev) => {
      if (prev.includes(id)) return prev;
      const updated = [...prev, id];
      try {
        localStorage.setItem("termShield_read_notifications", JSON.stringify(updated));
      } catch {
        // ignore storage errors
      }
      return updated;
    });
  };

  const markAllNotificationsAsRead = () => {
    const allIds = notifications.map((n) => n.id);
    setReadNotificationIds(allIds);
    try {
      localStorage.setItem("termShield_read_notifications", JSON.stringify(allIds));
    } catch {
      // ignore
    }
  };

  const handleNotificationClick = (notification) => {
    markNotificationAsRead(notification.id);
    if (notification.contractId) {
      handleContractSelect(notification.contractId);
    }
    setIsNotificationsOpen(false);
  };

  if (showSplash) {
    return <SplashScreen onComplete={() => setShowSplash(false)} />;
  }

  if (authState === "checking") {
    return (
      <main
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: "#060814",
          color: "#94a3b8",
          fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
          fontSize: "13px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Loader2 size={18} className="spin" style={{ color: "#38bdf8" }} />
          <span>Connecting to Term Shield...</span>
        </div>
      </main>
    );
  }

  if (authState === "unauthenticated") {
    const isLoginScreen = authScreen === "login";

    return (
      <div style={{ position: "relative", minHeight: "100vh" }}>
        {isLoginScreen ? (
          <Login
            onLoginSuccess={handleLoginSuccess}
            onSwitchToRegister={() => setAuthScreen("register")}
          />
        ) : (
          <Register onRegisterSuccess={handleRegisterSuccess} />
        )}

        {!isLoginScreen && (
          <div
            style={{
              position: "fixed",
              right: 0,
              bottom: "24px",
              left: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "7px",
              padding: "0 18px",
              color: "#64748b",
              fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
              fontSize: "12px",
            }}
          >
            <span>Already have an account?</span>
            <button
              type="button"
              onClick={() => setAuthScreen("login")}
              style={{
                padding: "4px 0",
                border: 0,
                background: "transparent",
                color: "#2563eb",
                font: "inherit",
                fontWeight: 700,
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              Sign in
            </button>
          </div>
        )}
      </div>
    );
  }

  const currentFullName =
    profileOverride.customFullName !== undefined &&
    profileOverride.customFullName !== null &&
    profileOverride.customFullName.trim() !== ""
      ? profileOverride.customFullName.trim()
      : currentUser?.full_name?.trim() || "";

  const userDisplayName =
    currentFullName || currentUser?.email || "Account";

  const userInitials = currentFullName
    ? currentFullName
        .split(/\s+/)
        .map((part) => part[0]?.toUpperCase())
        .slice(0, 2)
        .join("") || "TS"
    : currentUser?.email
      ? currentUser.email.slice(0, 2).toUpperCase()
      : "TS";

  const userPhoto = profileOverride.profilePhoto || null;

  return (
    <div className="app-shell">
      {/* MOBILE MENU */}
      <div
        className={`mobile-backdrop ${mobileMenu ? "show" : ""}`}
        onClick={() => setMobileMenu(false)}
      />

      {/* SIDEBAR */}
      <aside className={`sidebar ${mobileMenu ? "open" : ""}`}>
        <div className="sidebar-top">
          <div className="brand">
            <div className="brand-mark">
              <ShieldAlert size={20} />
            </div>

            <div className="brand-text">
              <strong>Term Shield</strong>
              <span>Contract Intelligence</span>
            </div>
          </div>

          <button
            className="mobile-close"
            type="button"
            onClick={() => setMobileMenu(false)}
          >
            <X size={18} />
          </button>
        </div>

        <nav className="nav-list">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.id;

            return (
              <button
                key={item.id}
                className={`nav-item ${isActive ? "active" : ""}`}
                type="button"
                onClick={() => handleNavigation(item.id)}
              >
                <Icon
                  size={18}
                  strokeWidth={isActive ? 2.2 : 1.9}
                />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <button
            type="button"
            className={`nav-item ${activePage === "settings" ? "active" : ""}`}
            onClick={() => handleNavigation("settings")}
          >
            <Settings size={18} />
            <span>Settings</span>
          </button>

          <div className="sidebar-profile-wrapper" ref={profileDropdownRef}>
            <button
              className={`sidebar-profile ${isProfileDropdownOpen ? "active" : ""}`}
              type="button"
              onClick={() => setIsProfileDropdownOpen((prev) => !prev)}
              aria-label="Account Settings"
              title="Account Menu"
              aria-expanded={isProfileDropdownOpen}
              style={{
                width: "100%",
                border: 0,
                background: "transparent",
                color: "inherit",
                font: "inherit",
                textAlign: "left",
                cursor: "pointer",
              }}
            >
              <div className="profile-avatar">
                {userPhoto ? (
                  <img src={userPhoto} alt={userDisplayName} className="profile-avatar-img" />
                ) : (
                  userInitials
                )}
              </div>

              <div className="profile-info">
                <strong>{userDisplayName}</strong>
                <span>{currentUser?.email || "Personal workspace"}</span>
              </div>

              <ChevronDown
                size={16}
                className={`profile-dropdown-arrow ${isProfileDropdownOpen ? "open" : ""}`}
              />
            </button>

            {isProfileDropdownOpen && (
              <div className="sidebar-profile-dropdown" role="menu">
                <div
                  className="sidebar-profile-dropdown-header"
                  onClick={() => {
                    setIsProfileDropdownOpen(false);
                    handleNavigation("settings");
                  }}
                  title="View Settings Profile"
                >
                  <div className="profile-avatar large">
                    {userPhoto ? (
                      <img src={userPhoto} alt={userDisplayName} className="profile-avatar-img" />
                    ) : (
                      userInitials
                    )}
                  </div>
                  <div className="profile-details">
                    <strong>{userDisplayName}</strong>
                    <span>{currentUser?.email || "Personal workspace"}</span>
                  </div>
                </div>

                <div className="profile-dropdown-divider" />

                <div className="profile-dropdown-menu">
                  <button
                    type="button"
                    className="profile-dropdown-item"
                    onClick={() => {
                      setIsProfileDropdownOpen(false);
                      setActiveModal("editProfile");
                    }}
                    role="menuitem"
                  >
                    <User size={15} />
                    <span>Edit Profile</span>
                  </button>

                  <button
                    type="button"
                    className="profile-dropdown-item"
                    onClick={() => {
                      setIsProfileDropdownOpen(false);
                      setActiveModal("help");
                    }}
                    role="menuitem"
                  >
                    <HelpCircle size={15} />
                    <span>Help &amp; Support</span>
                  </button>

                  <button
                    type="button"
                    className="profile-dropdown-item"
                    onClick={() => {
                      setIsProfileDropdownOpen(false);
                      setActiveModal("about");
                    }}
                    role="menuitem"
                  >
                    <Info size={15} />
                    <span>About Term Shield</span>
                  </button>

                  <button
                    type="button"
                    className="profile-dropdown-item"
                    onClick={() => {
                      setIsProfileDropdownOpen(false);
                      handleNavigation("settings");
                    }}
                    role="menuitem"
                  >
                    <Settings size={15} />
                    <span>Settings</span>
                  </button>

                  <div className="profile-dropdown-divider" />

                  <button
                    type="button"
                    className="profile-dropdown-item logout"
                    onClick={() => {
                      setIsProfileDropdownOpen(false);
                      handleLogout();
                    }}
                    role="menuitem"
                  >
                    <LogOut size={15} />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="mobile-menu-button"
              type="button"
              onClick={() => setMobileMenu(true)}
            >
              <Menu size={21} />
            </button>

            <div>
              <p className="breadcrumb">Workspace</p>
              <h1>
                {activePage === "ask"
                  ? "Ask My T&C"
                  : activeItem?.label || "Dashboard"}
              </h1>
            </div>
          </div>

          <div className="topbar-actions">
            <button
              className={`ask-button ${activePage === "ask" ? "active" : ""
                }`}
              type="button"
              onClick={() => handleNavigation("ask")}
              aria-label="Ask My T&C"
            >
              <MessageSquare size={16} />
              <span>Ask My T&C</span>
            </button>

            {/* SEARCH */}
            <div className="search-box-wrapper" ref={searchContainerRef}>
              <div
                className={`search-box ${isSearchOpen && searchQuery ? "focused" : ""}`}
                onClick={() => searchInputRef.current?.focus()}
              >
                <Search size={17} />
                <input
                  ref={searchInputRef}
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setIsSearchOpen(true);
                    setSearchSelectedIndex(-1);
                  }}
                  onFocus={() => {
                    if (searchQuery.trim()) {
                      setIsSearchOpen(true);
                    }
                  }}
                  onKeyDown={handleSearchKeyDown}
                  placeholder="Search contracts..."
                  aria-label="Search contracts"
                  aria-expanded={isSearchOpen && Boolean(searchQuery.trim())}
                  role="combobox"
                  aria-autocomplete="list"
                />
                {searchQuery ? (
                  <button
                    type="button"
                    className="search-clear-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSearchQuery("");
                      setIsSearchOpen(false);
                      setSearchSelectedIndex(-1);
                      searchInputRef.current?.focus();
                    }}
                    aria-label="Clear search"
                    title="Clear search"
                  >
                    <X size={14} />
                  </button>
                ) : (
                  <kbd>⌘ K</kbd>
                )}
              </div>

              {/* SEARCH DROPDOWN */}
              {isSearchOpen && searchQuery.trim().length > 0 && (
                <div
                  className="search-dropdown"
                  role="listbox"
                  aria-label="Search results"
                >
                  <div className="search-dropdown-header">
                    <span>
                      {filteredContracts.length === 0
                        ? "No matches"
                        : `${filteredContracts.length} contract${filteredContracts.length === 1 ? "" : "s"} found`}
                    </span>
                    <span className="search-shortcut-hint">
                      ↑↓ to navigate • ↵ to open
                    </span>
                  </div>

                  {filteredContracts.length === 0 ? (
                    <div className="search-empty">
                      <FileText size={22} className="search-empty-icon" />
                      <p className="search-empty-title">No contracts found</p>
                      <span className="search-empty-subtitle">
                        No contract matches &ldquo;{searchQuery}&rdquo; in your workspace
                      </span>
                    </div>
                  ) : (
                    <div className="search-results-list">
                      {filteredContracts.map((c, index) => {
                        const isSelected = index === searchSelectedIndex;
                        const risk = String(c?.overall_risk || "").toLowerCase();
                        const score = typeof c?.overall_risk_score === "number" ? c.overall_risk_score : null;
                        const dateStr = formatContractDate(c?.created_at);
                        const fileType = (c?.file_type || "doc").toUpperCase();

                        return (
                          <div
                            key={c.id || index}
                            className={`search-result-item ${isSelected ? "selected" : ""}`}
                            onClick={() => {
                              handleContractSelect(c.id);
                              setIsSearchOpen(false);
                              setSearchSelectedIndex(-1);
                            }}
                            onMouseEnter={() => setSearchSelectedIndex(index)}
                            role="option"
                            aria-selected={isSelected}
                          >
                            <div className="search-result-icon">
                              <FileText size={17} />
                            </div>

                            <div className="search-result-main">
                              <strong className="search-result-name">
                                {c.filename || c.name || "Untitled Contract"}
                              </strong>
                              <div className="search-result-meta">
                                <span>{dateStr}</span>
                                <span>•</span>
                                <span>{fileType}</span>
                              </div>
                            </div>

                            <div className="search-result-badge-wrap">
                              {risk === "high" || (score !== null && score >= 70) ? (
                                <span className="search-risk-badge high">
                                  HIGH RISK{score !== null ? ` • ${score}` : ""}
                                </span>
                              ) : risk === "medium" || risk === "med" || (score !== null && score >= 40) ? (
                                <span className="search-risk-badge medium">
                                  MED RISK{score !== null ? ` • ${score}` : ""}
                                </span>
                              ) : risk === "low" || (score !== null && score < 40) ? (
                                <span className="search-risk-badge low">
                                  LOW RISK{score !== null ? ` • ${score}` : ""}
                                </span>
                              ) : (
                                <span className="search-risk-badge neutral">
                                  DOC
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* NOTIFICATIONS */}
            <div className="notifications-wrapper" ref={notificationsRef}>
              <button
                className={`icon-button notification-bell-btn ${isNotificationsOpen ? "active" : ""}`}
                type="button"
                onClick={() => setIsNotificationsOpen((prev) => !prev)}
                aria-label="Notifications"
                aria-expanded={isNotificationsOpen}
                title="Notifications"
              >
                <Bell size={18} />
                {unreadCount > 0 && (
                  <span
                    className="notification-badge"
                    aria-label={`${unreadCount} unread notifications`}
                  >
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>

              {/* NOTIFICATIONS DROPDOWN */}
              {isNotificationsOpen && (
                <div
                  className="notifications-dropdown"
                  role="region"
                  aria-label="Notifications"
                >
                  <div className="notifications-dropdown-header">
                    <div className="notifications-title-row">
                      <h4>Notifications</h4>
                      {unreadCount > 0 && (
                        <span className="notifications-unread-pill">
                          {unreadCount} unread
                        </span>
                      )}
                    </div>
                    {unreadCount > 0 && (
                      <button
                        type="button"
                        className="mark-all-read-btn"
                        onClick={markAllNotificationsAsRead}
                      >
                        Mark all as read
                      </button>
                    )}
                  </div>

                  <div className="notifications-list">
                    {notifications.length === 0 ? (
                      <div className="notifications-empty">
                        <div className="notifications-empty-icon">
                          <CheckCircle2 size={24} />
                        </div>
                        <h4>You&apos;re all caught up</h4>
                        <p>No contract alerts or notifications at this time.</p>
                      </div>
                    ) : (
                      notifications.map((n) => {
                        const isRead = readNotificationIds.includes(n.id);
                        return (
                          <div
                            key={n.id}
                            className={`notification-item ${isRead ? "read" : "unread"}`}
                            onClick={() => handleNotificationClick(n)}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                handleNotificationClick(n);
                              }
                            }}
                          >
                            <div className={`notification-icon-wrap ${n.type}`}>
                              {n.type === "high_risk" ? (
                                <ShieldAlert size={16} />
                              ) : n.type === "medium_risk" ? (
                                <AlertCircle size={16} />
                              ) : n.type === "completed" ? (
                                <CheckCircle2 size={16} />
                              ) : (
                                <FileText size={16} />
                              )}
                            </div>

                            <div className="notification-content">
                              <div className="notification-item-header">
                                <span className="notification-item-title">
                                  {n.title}
                                </span>
                                {n.date && (
                                  <span className="notification-item-time">
                                    {formatNotificationTime(n.date)}
                                  </span>
                                )}
                              </div>
                              <p className="notification-item-msg">
                                {n.message}
                              </p>
                            </div>

                            {!isRead && (
                              <span
                                className="notification-unread-dot"
                                title="Unread"
                              />
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>

            <button
              className="top-profile"
              type="button"
              onClick={() => handleNavigation("settings")}
              title="Open Settings"
              aria-label="User Settings"
            >
              {userPhoto ? (
                <img src={userPhoto} alt={userDisplayName} className="top-profile-img" />
              ) : (
                userInitials
              )}
            </button>
          </div>
        </header>

        <main className="page-content">
          {/* DASHBOARD */}
          {activePage === "dashboard" && (
            <Dashboard
              onNavigate={handleNavigation}
              fileId={currentFileId}
              analysis={currentAnalysis}
              contracts={contracts}
              contractsLoading={contractsLoading}
              contractsError={contractsError}
              onRefresh={refreshContracts}
              onSelectContract={handleContractSelect}
              currentUser={currentUser}
            />
          )}

          {/* UPLOAD */}
          {activePage === "upload" && (
            <UploadContract
              onBack={() => handleNavigation("dashboard")}
              onAnalysisComplete={(fileId, analysis) => {
                setCurrentFileId(fileId);
                setCurrentAnalysis(analysis);
                setSelectedAnalysisLoading(false);
                setSelectedAnalysisError("");
                refreshContracts();
                handleNavigation("analysis");
              }}
            />
          )}

          {/* RISK ANALYSIS */}
          {activePage === "analysis" && (
            selectedAnalysisLoading ? (
              <AnalysisLoadingState />
            ) : selectedAnalysisError ? (
              <AnalysisErrorState
                message={selectedAnalysisError}
                onBack={() => handleNavigation("contracts")}
              />
            ) : (
              <RiskAnalysis
                fileId={currentFileId}
                analysis={currentAnalysis}
              />
            )
          )}

          {/* CONTRACTS */}
          {activePage === "contracts" && (
            <ContractsPage
              fileId={currentFileId}
              analysis={currentAnalysis}
              contracts={contracts}
              contractsLoading={contractsLoading}
              contractsError={contractsError}
              onSelectContract={handleContractSelect}
              onDeleteContract={handleDeleteContract}
              onNavigate={handleNavigation}
            />
          )}

          {/* CLAUSE EXPLORER */}
          {activePage === "clauses" && (
            <ClauseExplorer
              fileId={currentFileId}
              analysis={currentAnalysis}
            />
          )}

          {/* REPORTS */}
          {activePage === "reports" && (
            <ReportsPage
              fileId={currentFileId}
              analysis={currentAnalysis}
              onNavigate={handleNavigation}
            />
          )}

          {/* ASK MY T&C */}
          {activePage === "ask" && (
            <AskMyTC
              fileId={currentFileId}
              analysis={currentAnalysis}
            />
          )}

          {/* SETTINGS */}
          {activePage === "settings" && (
            <SettingsPage
              currentUser={currentUser}
              userLoading={userLoading}
              onLogout={handleLogout}
              onRefreshUser={fetchCurrentUser}
              userDisplayName={userDisplayName}
              userPhoto={userPhoto}
              userInitials={userInitials}
              onEditProfile={() => setActiveModal("editProfile")}
            />
          )}

          {/* OTHER PAGES */}
          {activePage !== "dashboard" &&
            activePage !== "upload" &&
            activePage !== "analysis" &&
            activePage !== "contracts" &&
            activePage !== "clauses" &&
            activePage !== "reports" &&
            activePage !== "ask" &&
            activePage !== "settings" && (
              <PlaceholderPage
                title={activeItem?.label || "Workspace"}
                description="This workspace will be connected to the Term Shield backend next."
              />
            )}
        </main>
      </div>

      {/* EDIT PROFILE MODAL */}
      {activeModal === "editProfile" && (
        <EditProfileModal
          initialName={currentFullName}
          initialPhoto={userPhoto}
          userInitials={userInitials}
          userEmail={currentUser?.email}
          onClose={() => setActiveModal(null)}
          onSave={(newName, newPhoto) => {
            const updated = {
              customFullName: newName.trim(),
              profilePhoto: newPhoto,
            };
            setProfileOverride(updated);
            try {
              localStorage.setItem(
                "termShield_profile_override",
                JSON.stringify(updated)
              );
            } catch {
              // ignore
            }
            setActiveModal(null);
          }}
        />
      )}

      {/* HELP & SUPPORT MODAL */}
      {activeModal === "help" && (
        <HelpSupportModal onClose={() => setActiveModal(null)} />
      )}

      {/* ABOUT TERM SHIELD MODAL */}
      {activeModal === "about" && (
        <AboutTermShieldModal onClose={() => setActiveModal(null)} />
      )}
    </div>
  );
}

/* =========================
   CLAUSE EXPLORER
========================= */

function ClauseExplorer({ fileId, analysis }) {
  const [explorerView, setExplorerView] = useState("list");
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [selectedClauseId, setSelectedClauseId] = useState(null);

  const clauses = Array.isArray(analysis)
    ? analysis
    : analysis?.analyses ||
    analysis?.clauses ||
    analysis?.results ||
    analysis?.data ||
    [];

  const normalizedClauses = clauses.map((clause, index) => {
    const risk = String(
      clause?.risk_level ||
      clause?.risk ||
      clause?.riskLevel ||
      "unknown"
    ).toLowerCase();
    const category =
      clause?.clause_type ||
      clause?.category ||
      clause?.classification ||
      "General clause";
    const title =
      clause?.title ||
      clause?.clause_title ||
      category ||
      `Clause ${index + 1}`;
    const explanation =
      clause?.meaning ||
      clause?.plain_language ||
      clause?.explanation ||
      clause?.summary ||
      "No explanation available.";
    const clauseText =
      clause?.text ||
      clause?.clause_text ||
      clause?.content ||
      explanation;
    const id = clause?.clause_id || clause?.id || `clause-${index}`;

    return {
      ...clause,
      id,
      title,
      category,
      risk,
      explanation,
      clauseText,
      score: clause?.risk_score ?? clause?.score ?? clause?.riskScore,
    };
  });

  const categories = [
    ...new Set(normalizedClauses.map((clause) => clause.category)),
  ];

  const visibleClauses = normalizedClauses.filter((clause) => {
    const search = searchTerm.trim().toLowerCase();
    const matchesSearch = [
      clause.title,
      clause.category,
      clause.explanation,
      clause.clauseText,
    ].some((value) =>
      String(value).toLowerCase().includes(search)
    );
    const matchesCategory =
      categoryFilter === "all" || clause.category === categoryFilter;
    const matchesRisk =
      riskFilter === "all" || clause.risk === riskFilter;

    return matchesSearch && matchesCategory && matchesRisk;
  });

  const selectedClause = normalizedClauses.find(
    (clause) => clause.id === selectedClauseId
  );

  const detailReasons = selectedClause
    ? Array.isArray(selectedClause.risk_reasons)
      ? selectedClause.risk_reasons
      : selectedClause.risk_reasons
        ? [selectedClause.risk_reasons]
        : []
    : [];
  const detailRecommendations = selectedClause
    ? Array.isArray(selectedClause.recommendations)
      ? selectedClause.recommendations
      : selectedClause.recommendations
        ? [selectedClause.recommendations]
        : []
    : [];

  return (
    <div className="clause-explorer-page">
      <section className="clause-explorer-header">
        <div>
          <span className="eyebrow">CLAUSE INTELLIGENCE</span>
          <h2>Explore every clause.</h2>
          <p>
            Search the analyzed language, examine inter-clause dependencies, and explore
            how clauses override or reference each other.
          </p>
        </div>

        <div className="clause-explorer-header-right">
          <div className="clause-view-toggle" role="tablist" aria-label="Clause Explorer View">
            <button
              type="button"
              role="tab"
              aria-selected={explorerView === "list"}
              className={`clause-view-toggle-btn ${explorerView === "list" ? "active" : ""}`}
              onClick={() => setExplorerView("list")}
            >
              <ListChecks size={15} />
              <span>Clause List</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={explorerView === "relationships"}
              className={`clause-view-toggle-btn ${explorerView === "relationships" ? "active" : ""}`}
              onClick={() => setExplorerView("relationships")}
            >
              <Network size={15} />
              <span>Clause Relationships</span>
            </button>
          </div>

          <div className="clause-explorer-count">
            <strong>{normalizedClauses.length}</strong>
            <span>clauses analyzed</span>
          </div>
        </div>
      </section>

      {explorerView === "list" ? (
        <>
          <section className="clause-explorer-toolbar" aria-label="Clause filters">
            <div className="clause-explorer-search">
              <Search size={17} />
              <input
                type="search"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search clauses, topics or explanations..."
                aria-label="Search clauses"
              />
            </div>

            <div className="clause-filter-group">
              <label>
                Category
                <select
                  value={categoryFilter}
                  onChange={(event) => setCategoryFilter(event.target.value)}
                >
                  <option value="all">All categories</option>
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Risk level
                <select
                  value={riskFilter}
                  onChange={(event) => setRiskFilter(event.target.value)}
                >
                  <option value="all">All risk levels</option>
                  <option value="high">High risk</option>
                  <option value="medium">Medium risk</option>
                  <option value="low">Low risk</option>
                  <option value="unknown">Unknown</option>
                </select>
              </label>
            </div>
          </section>

          <div className="clause-explorer-layout">
            <section className="clause-list-panel" aria-label="Clause list">
              <div className="clause-list-heading">
                <div>
                  <span className="card-label">ANALYZED CLAUSES</span>
                  <h3>{visibleClauses.length} visible</h3>
                </div>
                <span>Click a clause to inspect it</span>
              </div>

              {visibleClauses.length ? (
                <div className="clause-explorer-list">
                  {visibleClauses.map((clause, index) => (
                    <button
                      className={`clause-explorer-item ${selectedClause?.id === clause.id ? "selected" : ""
                        }`}
                      type="button"
                      key={clause.id}
                      onClick={() => setSelectedClauseId(clause.id)}
                    >
                      <span className="clause-explorer-number">
                        {String(index + 1).padStart(2, "0")}
                      </span>

                      <span className="clause-explorer-item-copy">
                        <strong>{clause.title}</strong>
                        <span>{clause.category}</span>
                        <small>{clause.explanation}</small>
                      </span>

                      <span className={`clause-explorer-risk ${clause.risk}`}>
                        {clause.score !== undefined && (
                          <b>{clause.score}</b>
                        )}
                        {clause.risk}
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="clause-explorer-empty compact">
                  <AlertCircle size={21} />
                  <strong>
                    {normalizedClauses.length
                      ? "No clauses match these filters"
                      : "No clause analysis available"}
                  </strong>
                  <span>
                    {normalizedClauses.length
                      ? "Try a different search term or reset the filters."
                      : "Analyze a contract to populate the Clause Explorer."}
                  </span>
                </div>
              )}
            </section>

            <section className="clause-detail-panel" aria-live="polite">
              {selectedClause ? (
                <>
                  <div className="clause-detail-header">
                    <div>
                      <span className="clause-number">
                        CLAUSE DETAIL
                      </span>
                      <h3>{selectedClause.title}</h3>
                      <span className="clause-detail-category">
                        {selectedClause.category}
                      </span>
                    </div>
                    <span className={`clause-explorer-risk ${selectedClause.risk}`}>
                      {selectedClause.risk}
                    </span>
                  </div>

                  <div className="clause-detail-score">
                    <span>Risk score</span>
                    <strong>
                      {selectedClause.score !== undefined
                        ? selectedClause.score
                        : "Not scored"}
                    </strong>
                  </div>

                  <ClauseDetailSection
                    icon={FileText}
                    title="Clause text"
                    text={selectedClause.clauseText}
                  />

                  <ClauseDetailSection
                    icon={AlertCircle}
                    title="Why it matters"
                    items={detailReasons.length ? detailReasons : [selectedClause.user_impact || selectedClause.explanation]}
                  />

                  <ClauseDetailSection
                    icon={ShieldAlert}
                    title="Risk explanation"
                    items={detailReasons.length ? detailReasons : [selectedClause.explanation]}
                  />

                  <ClauseDetailSection
                    icon={CheckCircle2}
                    title="Recommendation"
                    items={detailRecommendations.length ? detailRecommendations : ["No recommendation was provided for this clause."]}
                    tone="recommendation"
                  />
                </>
              ) : (
                <div className="clause-explorer-empty detail-empty">
                  <div className="clause-detail-empty-icon">
                    <ListChecks size={23} />
                  </div>
                  <span className="card-label">CLAUSE DETAIL</span>
                  <h3>Select a clause to begin</h3>
                  <p>
                    Choose an item from the list to view its text, risk context,
                    and recommended next steps.
                  </p>
                </div>
              )}
            </section>
          </div>
        </>
      ) : (
        <ClauseRelErrorBoundary>
          <ClauseRelationships
            fileId={fileId}
            clauses={normalizedClauses}
            onSelectClause={(clauseId) => {
              if (clauseId) {
                setSelectedClauseId(clauseId);
              }
              setExplorerView("list");
            }}
          />
        </ClauseRelErrorBoundary>
      )}
    </div>
  );
}

function ClauseDetailSection({
  icon: Icon,
  title,
  text,
  items,
  tone = "",
}) {
  return (
    <div className={`clause-detail-section ${tone}`}>
      <div className="clause-detail-section-heading">
        <Icon size={14} />
        <span>{title}</span>
      </div>
      {text ? <p>{text}</p> : null}
      {items ? (
        <ul>
          {items.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/* =========================
   CLAUSE RELATIONSHIPS
========================= */

const RELATIONSHIP_TYPES = {
  OVERRIDE: {
    label: "Override",
    color: "#dc2626",
    bgColor: "rgba(220, 38, 38, 0.08)",
    borderColor: "rgba(220, 38, 38, 0.28)",
    badgeColor: "#b91c1c",
    icon: "⚠️",
    dashed: false,
    description: "This clause supersedes, invalidates, or takes precedence over another clause.",
  },
  EXCEPTION: {
    label: "Exception",
    color: "#9333ea",
    bgColor: "rgba(147, 51, 234, 0.08)",
    borderColor: "rgba(147, 51, 234, 0.28)",
    badgeColor: "#7e22ce",
    icon: "⚡",
    dashed: true,
    description: "This clause carves out an exception or exemption from general contractual rules.",
  },
  DEPENDENCY: {
    label: "Dependency",
    color: "#d97706",
    bgColor: "rgba(217, 119, 6, 0.08)",
    borderColor: "rgba(217, 119, 6, 0.28)",
    badgeColor: "#b45309",
    icon: "🔗",
    dashed: true,
    description: "This clause depends on, requires prior completion of, or is conditioned upon another clause.",
  },
  CONDITION: {
    label: "Condition",
    color: "#059669",
    bgColor: "rgba(5, 150, 105, 0.08)",
    borderColor: "rgba(5, 150, 105, 0.28)",
    badgeColor: "#047857",
    icon: "⚖️",
    dashed: false,
    description: "Imposes prerequisites or legal triggers before rights or obligations take effect.",
  },
  MODIFICATION: {
    label: "Modification",
    color: "#db2777",
    bgColor: "rgba(219, 39, 119, 0.08)",
    borderColor: "rgba(219, 39, 119, 0.28)",
    badgeColor: "#be185d",
    icon: "✏️",
    dashed: false,
    description: "Amends, restricts, or extends terms established elsewhere in the contract.",
  },
  REFERENCE: {
    label: "Reference",
    color: "#2563eb",
    bgColor: "rgba(37, 99, 235, 0.08)",
    borderColor: "rgba(37, 99, 235, 0.28)",
    badgeColor: "#1d4ed8",
    icon: "↗️",
    dashed: false,
    description: "Directly cites or cross-references another provision for context or definitions.",
  },
  SUBCLAUSE: {
    label: "Subclause",
    color: "#0284c7",
    bgColor: "rgba(2, 132, 199, 0.08)",
    borderColor: "rgba(2, 132, 199, 0.28)",
    badgeColor: "#0369a1",
    icon: "↳",
    dashed: false,
    description: "Hierarchical sub-provision subordinate to a primary clause.",
  },
  DEFINITION: {
    label: "Definition",
    color: "#475569",
    bgColor: "rgba(71, 85, 105, 0.08)",
    borderColor: "rgba(71, 85, 105, 0.28)",
    badgeColor: "#334155",
    icon: "📖",
    dashed: false,
    description: "Provides a defined term or legal interpretation applied across the agreement.",
  },
};

function resolveClauseData(clauseId, clausesList = []) {
  if (!clauseId) return null;
  const strId = String(clauseId).trim();
  const safeList = Array.isArray(clausesList) ? clausesList : [];

  const matched = safeList.find((c) => {
    if (!c) return false;
    if (String(c.clause_id) === strId || String(c.id) === strId) return true;
    if (c.clause_number && String(c.clause_number).trim() === strId) return true;
    const stripped = strId.replace(/^clause[_-]/i, "");
    if (c.order !== undefined && String(c.order) === stripped) return true;
    if (c.clause_number && String(c.clause_number).trim() === stripped) return true;
    return false;
  });

  if (matched) {
    const num = matched.clause_number ? `Clause ${matched.clause_number}` : null;
    const rawTitle = matched.title || matched.category || `Clause ${strId}`;
    return {
      id: strId,
      resolved: true,
      title: rawTitle,
      number: matched.clause_number || null,
      displayLabel: num ? `${num}: ${rawTitle}` : rawTitle,
      shortLabel: num || (rawTitle.length > 18 ? rawTitle.slice(0, 16) + "..." : rawTitle),
      category: matched.category || "General clause",
      risk: String(matched.risk || "unknown").toLowerCase(),
      clauseText: matched.clauseText || matched.text || "",
      explanation: matched.explanation || "",
      score: matched.score,
    };
  }

  const cleanId = strId.replace(/^clause[_-]/i, "Clause ");
  return {
    id: strId,
    resolved: false,
    title: cleanId,
    number: null,
    displayLabel: cleanId,
    shortLabel: cleanId.length > 18 ? cleanId.slice(0, 15) + "..." : cleanId,
    category: "Referenced Section",
    risk: "unknown",
    clauseText: "",
    explanation: "Referenced provision in this agreement.",
    score: undefined,
  };
}

class ClauseRelErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ClauseRelationships error caught by boundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="clause-rel-container">
          <div className="clause-rel-error-card">
            <AlertCircle size={28} />
            <strong>Unable to render clause relationships</strong>
            <span>
              {this.state.error?.message || "An unexpected error occurred while mapping relationships."}
            </span>
            <button
              type="button"
              className="clause-rel-retry-btn"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Reset View
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function ClauseRelationships({ fileId, clauses = [], onSelectClause }) {
  const safeClauses = Array.isArray(clauses) ? clauses : [];
  const [relationshipsData, setRelationshipsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [typeFilter, setTypeFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRelIndex, setSelectedRelIndex] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);

  // Strict data isolation
  useEffect(() => {
    if (!fileId) {
      setRelationshipsData(null);
      setSelectedRelIndex(null);
      setSelectedNodeId(null);
      setLoading(false);
      setError(null);
      return undefined;
    }

    let isCancelled = false;

    // 1. Immediately clear old relationship state
    setRelationshipsData(null);
    setSelectedRelIndex(null);
    setSelectedNodeId(null);
    setError(null);
    setLoading(true);

    // 2. Fetch relationships for new fileId
    getContractRelationships(fileId)
      .then((data) => {
        // 3. Ignore stale responses
        if (isCancelled) return;

        // 4. Verify returned data matches current fileId or handle empty/null response
        if (data && (String(data.file_id) === String(fileId) || !data.file_id)) {
          setRelationshipsData(data);
        } else if (data === null || data === undefined) {
          setRelationshipsData({ relationships: [] });
        } else {
          setRelationshipsData(data || { relationships: [] });
        }
        setLoading(false);
      })
      .catch((err) => {
        if (isCancelled) return;
        console.error("Error loading clause relationships:", err);
        setError(
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "Unable to load clause relationships."
        );
        setLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [fileId]);

  const handleRetry = () => {
    if (!fileId) return;
    setLoading(true);
    setError(null);
    getContractRelationships(fileId)
      .then((data) => {
        setRelationshipsData(data || { relationships: [] });
        setLoading(false);
      })
      .catch((err) => {
        setError(
          err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "Unable to load clause relationships."
        );
        setLoading(false);
      });
  };

  const rawRelationships = Array.isArray(relationshipsData?.relationships)
    ? relationshipsData.relationships.filter((r) => r && typeof r === "object")
    : Array.isArray(relationshipsData)
      ? relationshipsData.filter((r) => r && typeof r === "object")
      : [];

  // Available types in current data
  const availableTypes = [
    ...new Set(
      rawRelationships.map((r) => (r.relationship_type || "").toUpperCase()).filter(Boolean)
    ),
  ];

  // Filtered relationships
  const typeFiltered =
    typeFilter === "all"
      ? rawRelationships
      : rawRelationships.filter(
        (r) => (r.relationship_type || "").toUpperCase() === typeFilter.toUpperCase()
      );

  const visibleRelationships = typeFiltered.filter((r) => {
    if (!r) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const src = resolveClauseData(r.source_clause_id, safeClauses);
    const tgt = resolveClauseData(r.target_clause_id, safeClauses);
    const relTypeStr = String(r.relationship_type || "").toLowerCase();
    const evidenceStr = String(r.evidence || "").toLowerCase();
    const srcTitleStr = String(src?.title || "").toLowerCase();
    const tgtTitleStr = String(tgt?.title || "").toLowerCase();
    return (
      relTypeStr.includes(q) ||
      evidenceStr.includes(q) ||
      srcTitleStr.includes(q) ||
      tgtTitleStr.includes(q)
    );
  });

  // Collect unique nodes for graph
  const uniqueNodeIds = [];
  visibleRelationships.forEach((r) => {
    if (r.source_clause_id && !uniqueNodeIds.includes(r.source_clause_id)) {
      uniqueNodeIds.push(r.source_clause_id);
    }
    if (r.target_clause_id && !uniqueNodeIds.includes(r.target_clause_id)) {
      uniqueNodeIds.push(r.target_clause_id);
    }
  });

  // Also include clauses referenced in evidence if target_clause_id is missing
  visibleRelationships.forEach((r) => {
    if (!r.target_clause_id && r.evidence) {
      const match = String(r.evidence).match(/\b(?:clause|section|article)\s*(\d+)/i);
      if (match) {
        const foundClause = safeClauses.find(
          (c) => String(c.clause_number) === match[1] || String(c.order) === match[1]
        );
        if (foundClause) {
          const idToAdd = foundClause.clause_id || foundClause.id || `clause-${match[1]}`;
          if (!uniqueNodeIds.includes(idToAdd)) {
            uniqueNodeIds.push(idToAdd);
          }
        }
      }
    }
  });

  const graphNodes = uniqueNodeIds
    .map((id) => resolveClauseData(id, safeClauses))
    .filter((node) => Boolean(node && node.id));

  // Helper to resolve target node ID for relationships
  const resolveRelationshipTarget = (rel, allGraphNodes = []) => {
    if (!rel) return null;
    const srcId = String(rel.source_clause_id || "").trim();

    // 1. Explicit target_clause_id match
    if (rel.target_clause_id) {
      const rawTgt = String(rel.target_clause_id).trim();
      const match = allGraphNodes.find(
        (n) =>
          n.id === rawTgt ||
          String(n.number) === rawTgt ||
          n.id.replace(/^clause[_-]/i, "") === rawTgt.replace(/^clause[_-]/i, "")
      );
      if (match) return match.id;
      return rawTgt;
    }

    // 2. Evidence text mentioning another clause in the graph
    const evidence = String(rel.evidence || "").toLowerCase();
    for (const node of allGraphNodes) {
      if (node.id === srcId) continue;
      const cleanId = node.id.replace(/^clause[_-]/i, "");
      const num = node.number ? String(node.number) : null;
      if (
        (num &&
          (evidence.includes(`clause ${num}`) ||
            evidence.includes(`section ${num}`) ||
            evidence.includes(`article ${num}`))) ||
        evidence.includes(node.id.toLowerCase()) ||
        (cleanId &&
          (evidence.includes(`clause ${cleanId}`) ||
            evidence.includes(`section ${cleanId}`)))
      ) {
        return node.id;
      }
    }

    // 3. In a 2-node graph, connect to the other node
    const otherNodes = allGraphNodes.filter((n) => n.id !== srcId);
    if (otherNodes.length === 1) {
      return otherNodes[0].id;
    }

    // 4. In a multi-node graph, fallback to first other node
    if (otherNodes.length > 0) {
      return otherNodes[0].id;
    }

    // 5. Single isolated node -> self
    return srcId;
  };

  // Compute node coordinates on elliptical canvas
  const canvasWidth = 760;
  const canvasHeight = 470;
  const cx = canvasWidth / 2;
  const cy = canvasHeight / 2;
  const rx = Math.min(275, canvasWidth * 0.38);
  const ry = Math.min(160, canvasHeight * 0.35);

  const nodeCoords = {};
  const totalNodes = graphNodes.length;
  graphNodes.forEach((node, idx) => {
    if (!node || !node.id) return;
    if (totalNodes === 1) {
      nodeCoords[node.id] = { x: cx, y: cy, angle: 0 };
    } else if (totalNodes === 2) {
      nodeCoords[node.id] = {
        x: idx === 0 ? cx - 180 : cx + 180,
        y: cy,
        angle: idx === 0 ? Math.PI : 0,
      };
    } else {
      const angle = (2 * Math.PI * idx) / totalNodes - Math.PI / 2;
      nodeCoords[node.id] = {
        x: cx + rx * Math.cos(angle),
        y: cy + ry * Math.sin(angle),
        angle,
      };
    }
  });

  const getNodeCoord = (clauseId) => {
    if (!clauseId) return null;
    const str = String(clauseId).trim();
    if (nodeCoords[str]) return nodeCoords[str];
    const stripped = str.replace(/^clause[_-]/i, "");
    for (const [key, val] of Object.entries(nodeCoords)) {
      if (key === stripped || key.replace(/^clause[_-]/i, "") === stripped) {
        return val;
      }
    }
    return null;
  };

  // Group relationships by connected pair to prevent overlapping edges
  const pairCounts = {};
  const pairIndices = [];
  visibleRelationships.forEach((rel) => {
    const tgtId = resolveRelationshipTarget(rel, graphNodes);
    const srcId = rel.source_clause_id;
    const pairKey = [srcId, tgtId].sort().join("---");
    const idxInPair = pairCounts[pairKey] || 0;
    pairIndices.push(idxInPair);
    pairCounts[pairKey] = idxInPair + 1;
  });

  // Selected relationship or node
  const selectedRel =
    selectedRelIndex !== null && visibleRelationships[selectedRelIndex]
      ? visibleRelationships[selectedRelIndex]
      : null;

  const selectedNode =
    selectedNodeId ? resolveClauseData(selectedNodeId, safeClauses) : null;

  const selectedNodeRels = selectedNode
    ? rawRelationships.filter((r) => {
      if (!r) return false;
      const tgtId = resolveRelationshipTarget(r, graphNodes);
      return r.source_clause_id === selectedNode.id || tgtId === selectedNode.id;
    })
    : [];

  const getRiskBadgeColor = (risk) => {
    switch (String(risk).toLowerCase()) {
      case "high":
        return "#ef4444";
      case "medium":
        return "#f59e0b";
      case "low":
        return "#10b981";
      default:
        return "#94a3b8";
    }
  };

  return (
    <div className="clause-rel-container">
      {/* Toolbar */}
      <section className="clause-rel-toolbar" aria-label="Relationship filters">
        <div className="clause-rel-search">
          <Search size={15} />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by clause, term, or evidence text..."
            aria-label="Filter relationships"
          />
        </div>

        <div className="clause-rel-type-pills" role="radiogroup" aria-label="Relationship type filter">
          <button
            type="button"
            className={`clause-rel-type-pill ${typeFilter === "all" ? "active" : ""}`}
            onClick={() => setTypeFilter("all")}
          >
            All Types
            <span className="clause-rel-pill-badge">{rawRelationships.length}</span>
          </button>
          {availableTypes.map((type) => {
            const cfg = RELATIONSHIP_TYPES[type] || { label: type, color: "#64748b" };
            const count = rawRelationships.filter(
              (r) => (r.relationship_type || "").toUpperCase() === type
            ).length;
            return (
              <button
                key={type}
                type="button"
                className={`clause-rel-type-pill ${typeFilter === type ? "active" : ""}`}
                style={{
                  "--pill-color": cfg.color,
                }}
                onClick={() => setTypeFilter(typeFilter === type ? "all" : type)}
              >
                <span>{cfg.icon}</span>
                <span>{cfg.label}</span>
                <span className="clause-rel-pill-badge">{count}</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Main Content Area */}
      {loading ? (
        <div className="clause-rel-loading-card">
          <Loader2 size={28} className="spin" />
          <strong>Mapping Clause Relationships</strong>
          <span>Extracting cross-references, dependencies, and overrides from this contract...</span>
        </div>
      ) : error ? (
        <div className="clause-rel-error-card">
          <AlertCircle size={28} />
          <strong>Failed to load relationships</strong>
          <span>{error}</span>
          <button type="button" className="clause-rel-retry-btn" onClick={handleRetry}>
            Try Again
          </button>
        </div>
      ) : !fileId ? (
        <div className="clause-rel-empty-card">
          <div className="clause-rel-empty-icon">
            <Network size={26} />
          </div>
          <span className="card-label">NO CONTRACT SELECTED</span>
          <h3>Select a contract to view relationships</h3>
          <p>Choose an analyzed contract from your Contracts Library to map out cross-clause dependencies.</p>
        </div>
      ) : rawRelationships.length === 0 ? (
        <div className="clause-rel-empty-card">
          <div className="clause-rel-empty-icon">
            <Network size={26} />
          </div>
          <span className="card-label">RELATIONSHIP ANALYSIS</span>
          <h3>No clause relationships detected</h3>
          <p>
            This agreement contains independent provisions with no explicit cross-references,
            overrides, or conditional dependencies detected between clauses.
          </p>
          <button
            type="button"
            className="clause-rel-return-btn"
            onClick={() => onSelectClause && onSelectClause(null)}
          >
            Return to Clause List
          </button>
        </div>
      ) : (
        <div className="clause-rel-layout">
          {/* Graph Visualizer Panel */}
          <div className="clause-rel-graph-panel">
            <div className="clause-rel-graph-header">
              <div>
                <span className="card-label">DEPENDENCY GRAPH</span>
                <h3>
                  {visibleRelationships.length}{" "}
                  {visibleRelationships.length === 1 ? "Connection" : "Connections"} ·{" "}
                  {graphNodes.length} Linked Clauses
                </h3>
              </div>
              <div className="clause-rel-graph-actions">
                {(selectedRelIndex !== null || selectedNodeId !== null) && (
                  <button
                    type="button"
                    className="clause-rel-reset-btn"
                    onClick={() => {
                      setSelectedRelIndex(null);
                      setSelectedNodeId(null);
                    }}
                  >
                    Reset view
                  </button>
                )}
                <span className="clause-rel-hint">Click node or line to inspect</span>
              </div>
            </div>

            <div className="clause-rel-svg-wrap">
              <svg
                viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
                preserveAspectRatio="xMidYMid meet"
                className="clause-rel-svg"
                onClick={(e) => {
                  if (e.target.tagName === "svg") {
                    setSelectedRelIndex(null);
                    setSelectedNodeId(null);
                  }
                }}
              >
                {/* SVG Marker Definitions for Directed Arrowheads */}
                <defs>
                  {Object.entries(RELATIONSHIP_TYPES).map(([typeKey, cfg]) => (
                    <marker
                      key={typeKey}
                      id={`rel-arrow-${typeKey}`}
                      viewBox="0 0 10 10"
                      refX="8"
                      refY="5"
                      markerWidth="7"
                      markerHeight="7"
                      orient="auto"
                    >
                      <path d="M 1 2 L 8 5 L 1 8 z" fill={cfg.color || "#7c3aed"} />
                    </marker>
                  ))}
                  <marker
                    id="rel-arrow-DEFAULT"
                    viewBox="0 0 10 10"
                    refX="8"
                    refY="5"
                    markerWidth="7"
                    markerHeight="7"
                    orient="auto"
                  >
                    <path d="M 1 2 L 8 5 L 1 8 z" fill="#7c3aed" />
                  </marker>
                  <filter id="rel-glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="1" stdDeviation="2" floodColor="#8f744f" floodOpacity="0.3" />
                  </filter>
                  <filter id="edge-label-shadow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="1" stdDeviation="1.5" floodColor="#000000" floodOpacity="0.12" />
                  </filter>
                </defs>

                {/* Center circle guide */}
                <g opacity="0.25">
                  <circle cx={cx} cy={cy} r={rx} fill="none" stroke="#e2ddd4" strokeDasharray="3,6" />
                </g>

                {/* Connection Edges */}
                {visibleRelationships.map((rel, idx) => {
                  const src = getNodeCoord(rel.source_clause_id);
                  const tgtId = resolveRelationshipTarget(rel, graphNodes);
                  const tgt = getNodeCoord(tgtId);
                  const typeKey = (rel.relationship_type || "REFERENCE").toUpperCase();
                  const cfg = RELATIONSHIP_TYPES[typeKey] || RELATIONSHIP_TYPES.REFERENCE;

                  if (!src) return null;

                  const isSelfLoop = !tgt || rel.source_clause_id === tgtId || (src.x === tgt.x && src.y === tgt.y);

                  let pathD = "";
                  let labelPos = { x: src.x, y: src.y - 45 };

                  if (!isSelfLoop && tgt) {
                    const pairKey = [rel.source_clause_id, tgtId].sort().join("---");
                    const totalInPair = pairCounts[pairKey] || 1;
                    const idxInPair = pairIndices[idx] || 0;

                    let offset = 0;
                    if (totalInPair === 1) offset = -22;
                    else if (totalInPair === 2) offset = idxInPair === 0 ? -45 : 45;
                    else if (totalInPair === 3) offset = idxInPair === 0 ? -55 : idxInPair === 1 ? 0 : 55;
                    else offset = ((idxInPair - (totalInPair - 1) / 2) / ((totalInPair - 1) / 2)) * 75;

                    // Consistent canonical orientation for control point offset
                    const [canonSrcId, canonTgtId] = [rel.source_clause_id, tgtId].slice().sort();
                    const canonSrc = getNodeCoord(canonSrcId) || src;
                    const canonTgt = getNodeCoord(canonTgtId) || tgt;
                    const cdx = canonTgt.x - canonSrc.x;
                    const cdy = canonTgt.y - canonSrc.y;
                    const cdist = Math.hypot(cdx, cdy) || 1;
                    const cnx = -cdy / cdist;
                    const cny = cdx / cdist;

                    const midX = (src.x + tgt.x) / 2;
                    const midY = (src.y + tgt.y) / 2;
                    const cpx = midX + cnx * offset;
                    const cpy = midY + cny * offset;

                    // Calculate boundary exits so arrowhead and lines are outside the 110x34px node pills
                    const hw = 58;
                    const hh = 20;

                    const s_dx = cpx - src.x;
                    const s_dy = cpy - src.y;
                    const s_angle = Math.atan2(s_dy, s_dx);
                    const s_r = (hw * hh) / Math.sqrt((hh * Math.cos(s_angle)) ** 2 + (hw * Math.sin(s_angle)) ** 2);
                    const startX = src.x + Math.cos(s_angle) * (s_r + 2);
                    const startY = src.y + Math.sin(s_angle) * (s_r + 2);

                    const t_dx = tgt.x - cpx;
                    const t_dy = tgt.y - cpy;
                    const t_angle = Math.atan2(t_dy, t_dx);
                    const t_r = (hw * hh) / Math.sqrt((hh * Math.cos(t_angle)) ** 2 + (hw * Math.sin(t_angle)) ** 2);
                    const endX = tgt.x - Math.cos(t_angle) * (t_r + 6);
                    const endY = tgt.y - Math.sin(t_angle) * (t_r + 6);

                    if (Number.isFinite(startX) && Number.isFinite(startY) && Number.isFinite(endX) && Number.isFinite(endY)) {
                      pathD = offset === 0
                        ? `M ${startX.toFixed(1)} ${startY.toFixed(1)} L ${endX.toFixed(1)} ${endY.toFixed(1)}`
                        : `M ${startX.toFixed(1)} ${startY.toFixed(1)} Q ${cpx.toFixed(1)} ${cpy.toFixed(1)} ${endX.toFixed(1)} ${endY.toFixed(1)}`;
                      labelPos = {
                        x: 0.25 * startX + 0.5 * cpx + 0.25 * endX,
                        y: 0.25 * startY + 0.5 * cpy + 0.25 * endY,
                      };
                    } else {
                      pathD = `M ${src.x} ${src.y} L ${tgt.x} ${tgt.y}`;
                      labelPos = { x: midX, y: midY };
                    }
                  } else {
                    // Outward self-loop positioned clearly above the node pill
                    const loopH = 48;
                    const loopStartX = src.x - 22;
                    const loopStartY = src.y - 17;
                    const loopEndX = src.x + 22;
                    const loopEndY = src.y - 17;
                    pathD = `M ${loopStartX} ${loopStartY} C ${src.x - 40} ${src.y - 17 - loopH}, ${src.x + 40} ${src.y - 17 - loopH}, ${loopEndX} ${loopEndY}`;
                    labelPos = { x: src.x, y: src.y - 17 - loopH + 4 };
                  }

                  const isSelected = selectedRelIndex === idx;
                  const isConnectedToSelectedNode =
                    selectedNodeId &&
                    (rel.source_clause_id === selectedNodeId || tgtId === selectedNodeId);
                  const isHighlighted = isSelected || isConnectedToSelectedNode;
                  const isDimmed =
                    (selectedRelIndex !== null || selectedNodeId !== null) &&
                    !isHighlighted;

                  const labelText = `${cfg.icon} ${cfg.label}`;
                  const labelWidth = Math.max(78, labelText.length * 6.5 + 16);

                  return (
                    <g key={`edge-${idx}`} className="clause-rel-edge-group">
                      {/* Transparent wide stroke for easy clicking/hover */}
                      <path
                        d={pathD}
                        fill="none"
                        stroke="transparent"
                        strokeWidth="22"
                        style={{ cursor: "pointer" }}
                        onClick={() => {
                          setSelectedRelIndex(idx);
                          setSelectedNodeId(null);
                        }}
                      />
                      {/* Visible connection path */}
                      <path
                        d={pathD}
                        fill="none"
                        stroke={cfg.color || "#7c3aed"}
                        strokeWidth={isHighlighted ? 3.5 : 2.6}
                        strokeDasharray={cfg.dashed ? "6,4" : "none"}
                        opacity={isDimmed ? 0.2 : 1}
                        markerEnd={`url(#rel-arrow-${typeKey})`}
                        style={{
                          transition: "stroke-width 0.2s, opacity 0.2s",
                          pointerEvents: "none",
                        }}
                      />
                      {/* Edge Label Badge */}
                      <g
                        className="clause-rel-edge-label"
                        transform={`translate(${labelPos.x.toFixed(1)}, ${labelPos.y.toFixed(1)})`}
                        style={{ cursor: "pointer", opacity: isDimmed ? 0.25 : 1 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedRelIndex(idx);
                          setSelectedNodeId(null);
                        }}
                      >
                        <rect
                          x={(-labelWidth / 2).toFixed(1)}
                          y="-11"
                          width={labelWidth}
                          height="22"
                          rx="11"
                          fill="#ffffff"
                          stroke={isHighlighted ? cfg.color : "#d5d1c8"}
                          strokeWidth={isHighlighted ? 2.2 : 1.2}
                          filter="url(#edge-label-shadow)"
                        />
                        <text
                          x="0"
                          y="3.5"
                          textAnchor="middle"
                          fontSize="9.5"
                          fontWeight={isHighlighted ? "700" : "600"}
                          fill={cfg.badgeColor || cfg.color || "#334155"}
                          style={{ userSelect: "none" }}
                        >
                          {labelText}
                        </text>
                      </g>
                    </g>
                  );
                })}

                {/* Clause Nodes */}
                {graphNodes.map((node) => {
                  const pos = nodeCoords[node.id];
                  if (!pos) return null;

                  const isSelected = selectedNodeId === node.id;
                  const isConnectedToSelectedRel =
                    selectedRel &&
                    (selectedRel.source_clause_id === node.id ||
                      selectedRel.target_clause_id === node.id);
                  const isHighlighted = isSelected || isConnectedToSelectedRel;
                  const isDimmed =
                    (selectedNodeId !== null || selectedRel !== null) &&
                    !isHighlighted;

                  const riskColor = getRiskBadgeColor(node.risk);

                  return (
                    <g
                      key={`node-${node.id}`}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      className={`clause-rel-node ${isHighlighted ? "highlighted" : ""} ${isDimmed ? "dimmed" : ""
                        }`}
                      style={{ cursor: "pointer", transition: "all 0.2s" }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNodeId(selectedNodeId === node.id ? null : node.id);
                        setSelectedRelIndex(null);
                      }}
                    >
                      {/* Node Box Pill */}
                      <rect
                        x="-55"
                        y="-17"
                        width="110"
                        height="34"
                        rx="17"
                        fill={isHighlighted ? "#19191f" : "#ffffff"}
                        stroke={isHighlighted ? "#8f744f" : "#d9d6ce"}
                        strokeWidth={isHighlighted ? 2.4 : 1.2}
                        filter={isHighlighted ? "url(#rel-glow)" : "none"}
                      />
                      {/* Risk Dot */}
                      <circle
                        cx="-42"
                        cy="0"
                        r="4"
                        fill={riskColor}
                      />
                      {/* Section Title */}
                      <text
                        x="-32"
                        y="3.5"
                        fontSize="9.5"
                        fontWeight={isHighlighted ? "700" : "600"}
                        fill={isHighlighted ? "#ffffff" : "#2a2a32"}
                        textAnchor="start"
                      >
                        {node.shortLabel}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* Visual Legend */}
            <div className="clause-rel-legend">
              <span className="clause-rel-legend-title">Types:</span>
              <div className="clause-rel-legend-items">
                {Object.entries(RELATIONSHIP_TYPES).map(([typeKey, cfg]) => {
                  const hasThisType = availableTypes.includes(typeKey);
                  return (
                    <div
                      key={typeKey}
                      className={`clause-rel-legend-item ${hasThisType ? "active" : "inactive"}`}
                    >
                      <span
                        className="clause-rel-legend-dot"
                        style={{ background: cfg.color }}
                      />
                      <span>{cfg.label}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Evidence / Details Inspector Panel */}
          <div className="clause-rel-details-panel">
            {selectedRel ? (
              // RELATIONSHIP EVIDENCE VIEW
              <div className="clause-rel-inspect-content">
                <div className="clause-rel-inspect-header">
                  <div className="clause-rel-inspect-badge-row">
                    {(() => {
                      const typeKey = (selectedRel.relationship_type || "REFERENCE").toUpperCase();
                      const cfg = RELATIONSHIP_TYPES[typeKey] || RELATIONSHIP_TYPES.REFERENCE;
                      return (
                        <span
                          className="clause-rel-type-tag"
                          style={{
                            background: cfg.bgColor,
                            borderColor: cfg.borderColor,
                            color: cfg.badgeColor,
                          }}
                        >
                          {cfg.icon} {cfg.label.toUpperCase()}
                        </span>
                      );
                    })()}
                    <span className="clause-rel-confidence-tag">
                      {Math.round((selectedRel.confidence ?? 1.0) * 100)}% confidence
                    </span>
                  </div>

                  <button
                    type="button"
                    className="clause-rel-close-btn"
                    onClick={() => setSelectedRelIndex(null)}
                    aria-label="Close details"
                  >
                    <X size={15} />
                  </button>
                </div>

                {/* Clause Flow Box */}
                {(() => {
                  const src = resolveClauseData(selectedRel.source_clause_id, clauses);
                  const resolvedTgtId = resolveRelationshipTarget(selectedRel, graphNodes);
                  const tgt = resolveClauseData(selectedRel.target_clause_id || resolvedTgtId, clauses);
                  const typeKey = (selectedRel.relationship_type || "REFERENCE").toUpperCase();
                  const cfg = RELATIONSHIP_TYPES[typeKey] || RELATIONSHIP_TYPES.REFERENCE;

                  return (
                    <div className="clause-rel-flow-container">
                      <div className="clause-rel-flow-card">
                        <span className="flow-role">SOURCE CLAUSE</span>
                        <strong>{src?.displayLabel}</strong>
                        <div className="flow-meta">
                          <span>{src?.category}</span>
                          <span className={`flow-risk ${src?.risk}`}>{src?.risk} risk</span>
                        </div>
                      </div>

                      <div className="clause-rel-flow-arrow" style={{ color: cfg.color }}>
                        <ArrowRight size={18} />
                        <small>{cfg.label}</small>
                      </div>

                      <div className="clause-rel-flow-card">
                        <span className="flow-role">TARGET CLAUSE</span>
                        <strong>{tgt ? tgt.displayLabel : "Agreement Scope"}</strong>
                        <div className="flow-meta">
                          <span>{tgt ? tgt.category : "General provisions"}</span>
                          {tgt && <span className={`flow-risk ${tgt.risk}`}>{tgt.risk} risk</span>}
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* Legal Effect Description */}
                {(() => {
                  const typeKey = (selectedRel.relationship_type || "REFERENCE").toUpperCase();
                  const cfg = RELATIONSHIP_TYPES[typeKey] || RELATIONSHIP_TYPES.REFERENCE;
                  return (
                    <div className="clause-rel-description-box">
                      <span className="card-label">LEGAL MEANING</span>
                      <p>{cfg.description}</p>
                    </div>
                  );
                })()}

                {/* Evidence Callout */}
                <div className="clause-rel-evidence-box">
                  <div className="clause-rel-evidence-header">
                    <Sparkles size={14} />
                    <span>CONTRACT EVIDENCE</span>
                  </div>
                  <blockquote>
                    "{selectedRel.evidence || "Direct cross-reference identified in clause language."}"
                  </blockquote>
                </div>

                {/* Action Links */}
                <div className="clause-rel-actions">
                  <button
                    type="button"
                    className="clause-rel-view-link"
                    onClick={() => onSelectClause && onSelectClause(selectedRel.source_clause_id)}
                  >
                    View Source in Clause List
                  </button>
                  {selectedRel.target_clause_id && (
                    <button
                      type="button"
                      className="clause-rel-view-link secondary"
                      onClick={() => onSelectClause && onSelectClause(selectedRel.target_clause_id)}
                    >
                      View Target in Clause List
                    </button>
                  )}
                </div>
              </div>
            ) : selectedNode ? (
              // NODE DETAIL VIEW
              <div className="clause-rel-inspect-content">
                <div className="clause-rel-inspect-header">
                  <div>
                    <span className="card-label">SELECTED CLAUSE</span>
                    <h3>{selectedNode.displayLabel}</h3>
                  </div>
                  <button
                    type="button"
                    className="clause-rel-close-btn"
                    onClick={() => setSelectedNodeId(null)}
                    aria-label="Close details"
                  >
                    <X size={15} />
                  </button>
                </div>

                <div className="clause-rel-node-meta">
                  <span>{selectedNode.category}</span>
                  <span className={`clause-explorer-risk ${selectedNode.risk}`}>
                    {selectedNode.risk} risk
                  </span>
                  {selectedNode.score !== undefined && (
                    <span className="clause-rel-score-badge">Score {selectedNode.score}</span>
                  )}
                </div>

                {selectedNode.explanation && (
                  <div className="clause-rel-node-snippet">
                    <span className="card-label">EXPLANATION</span>
                    <p>{selectedNode.explanation}</p>
                  </div>
                )}

                {/* Connected Relationships for this node */}
                <div className="clause-rel-connected-section">
                  <span className="card-label">
                    CONNECTED RELATIONSHIPS ({selectedNodeRels.length})
                  </span>

                  {selectedNodeRels.length > 0 ? (
                    <div className="clause-rel-connected-list">
                      {selectedNodeRels.map((rel, i) => {
                        const isOutgoing = rel.source_clause_id === selectedNode.id;
                        const resolvedTgtId = resolveRelationshipTarget(rel, graphNodes);
                        const otherId = isOutgoing
                          ? (rel.target_clause_id || resolvedTgtId)
                          : rel.source_clause_id;
                        const otherClause = resolveClauseData(otherId, clauses);
                        const typeKey = (rel.relationship_type || "REFERENCE").toUpperCase();
                        const cfg = RELATIONSHIP_TYPES[typeKey] || RELATIONSHIP_TYPES.REFERENCE;

                        return (
                          <button
                            key={i}
                            type="button"
                            className="clause-rel-connected-item"
                            onClick={() => {
                              const relIdx = visibleRelationships.indexOf(rel);
                              if (relIdx !== -1) {
                                setSelectedRelIndex(relIdx);
                                setSelectedNodeId(null);
                              }
                            }}
                          >
                            <div className="connected-item-top">
                              <span
                                className="clause-rel-type-tag compact"
                                style={{
                                  background: cfg.bgColor,
                                  borderColor: cfg.borderColor,
                                  color: cfg.badgeColor,
                                }}
                              >
                                {cfg.icon} {cfg.label}
                              </span>
                              <span className="connected-direction">
                                {isOutgoing ? "Targets →" : "← Sourced from"}
                              </span>
                            </div>
                            <strong className="connected-partner-title">
                              {otherClause ? otherClause.displayLabel : "Agreement Scope"}
                            </strong>
                            <small className="connected-evidence">
                              "{rel.evidence ? String(rel.evidence).slice(0, 110) : ""}..."
                            </small>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="clause-rel-no-conn">No cross-clause links for this clause.</p>
                  )}
                </div>

                <div className="clause-rel-actions">
                  <button
                    type="button"
                    className="clause-rel-view-link"
                    onClick={() => onSelectClause && onSelectClause(selectedNode.id)}
                  >
                    Open in Clause List
                  </button>
                </div>
              </div>
            ) : (
              // DEFAULT OVERVIEW VIEW
              <div className="clause-rel-inspect-content">
                <div className="clause-rel-default-header">
                  <div className="clause-rel-default-icon">
                    <Share2 size={22} />
                  </div>
                  <span className="card-label">RELATIONSHIP INTELLIGENCE</span>
                  <h3>Cross-Clause Interactions</h3>
                  <p>
                    Click any node or link in the graph to view exact legal evidence,
                    cross-references, and override triggers.
                  </p>
                </div>

                {/* Quick Stats Grid */}
                <div className="clause-rel-stats-grid">
                  <div className="clause-rel-stat-box">
                    <strong>{rawRelationships.length}</strong>
                    <span>Total Links</span>
                  </div>
                  <div className="clause-rel-stat-box">
                    <strong>{graphNodes.length}</strong>
                    <span>Clauses Connected</span>
                  </div>
                  <div className="clause-rel-stat-box">
                    <strong>{availableTypes.length}</strong>
                    <span>Relationship Types</span>
                  </div>
                </div>

                {/* Interactive Relationship Cards List */}
                <div className="clause-rel-summary-list">
                  <span className="card-label">ALL DETECTED CONNECTIONS</span>
                  <div className="clause-rel-card-scroll">
                    {visibleRelationships.length === 0 ? (
                      <div className="clause-rel-no-conn" style={{ textAlign: "center", padding: "1.5rem" }}>
                        No relationships match your search or filter.
                      </div>
                    ) : (
                      visibleRelationships.map((rel, idx) => {
                        const src = resolveClauseData(rel.source_clause_id, safeClauses);
                        const tgt = resolveClauseData(rel.target_clause_id, safeClauses);
                        const typeKey = (rel.relationship_type || "REFERENCE").toUpperCase();
                        const cfg = RELATIONSHIP_TYPES[typeKey] || RELATIONSHIP_TYPES.REFERENCE;

                        return (
                          <button
                            key={idx}
                            type="button"
                            className="clause-rel-summary-card"
                            onClick={() => {
                              setSelectedRelIndex(idx);
                              setSelectedNodeId(null);
                            }}
                          >
                            <div className="summary-card-top">
                              <span
                                className="clause-rel-type-tag compact"
                                style={{
                                  background: cfg.bgColor,
                                  borderColor: cfg.borderColor,
                                  color: cfg.badgeColor,
                                }}
                              >
                                {cfg.icon} {cfg.label}
                              </span>
                              <span className="summary-card-conf">
                                {Math.round((rel.confidence ?? 1.0) * 100)}%
                              </span>
                            </div>

                            <div className="summary-card-flow">
                              <span>{src?.displayLabel}</span>
                              <ArrowRight size={12} style={{ color: cfg.color }} />
                              <span>{tgt ? tgt.displayLabel : "Agreement Scope"}</span>
                            </div>

                            <small className="summary-card-snippet">
                              "{rel.evidence ? String(rel.evidence).slice(0, 95) : ""}..."
                            </small>
                          </button>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* =========================
   REPORTS PAGE
========================= */

function ReportsPage({ fileId, analysis: passedAnalysis, onNavigate }) {
  const [summaryData, setSummaryData] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [relationshipsData, setRelationshipsData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [summaryError, setSummaryError] = useState("");
  const [relationshipsError, setRelationshipsError] = useState("");
  const [generatedDate, setGeneratedDate] = useState(() => new Date().toLocaleString());

  const fetchReportData = async (targetFileId) => {
    if (!targetFileId) {
      setSummaryData(null);
      setAnalysisData(null);
      setRelationshipsData(null);
      setLoading(false);
      setError("");
      return;
    }

    setLoading(true);
    setError("");
    setSummaryError("");
    setRelationshipsError("");
    setGeneratedDate(new Date().toLocaleString());

    const requests = [
      getContractSummary(targetFileId)
        .then((data) => ({ status: "fulfilled", type: "summary", data }))
        .catch((err) => ({ status: "rejected", type: "summary", err })),

      (passedAnalysis?.analyses || passedAnalysis?.clauses || Array.isArray(passedAnalysis)
        ? Promise.resolve({
          status: "fulfilled",
          type: "analysis",
          data: passedAnalysis,
        })
        : getContractAnalysis(targetFileId)
          .then((data) => ({ status: "fulfilled", type: "analysis", data }))
          .catch((err) => ({ status: "rejected", type: "analysis", err }))
      ),

      getContractRelationships(targetFileId)
        .then((data) => ({ status: "fulfilled", type: "relationships", data }))
        .catch((err) => ({ status: "rejected", type: "relationships", err })),
    ];

    try {
      const results = await Promise.allSettled(requests);
      let hadAnySuccess = false;

      results.forEach((res) => {
        if (res.status === "fulfilled") {
          const item = res.value;
          if (item.status === "fulfilled") {
            hadAnySuccess = true;
            if (item.type === "summary") setSummaryData(item.data);
            if (item.type === "analysis") setAnalysisData(item.data);
            if (item.type === "relationships") setRelationshipsData(item.data);
          } else {
            if (item.type === "summary") {
              setSummaryError(item.err?.response?.data?.detail || "Summary data could not be retrieved.");
            }
            if (item.type === "relationships") {
              setRelationshipsError(item.err?.response?.data?.detail || "Relationship data could not be retrieved.");
            }
          }
        }
      });

      if (passedAnalysis && !analysisData) {
        setAnalysisData(passedAnalysis);
        hadAnySuccess = true;
      }

      if (!hadAnySuccess) {
        setError("Unable to generate report. Failed to retrieve contract analysis data.");
      }
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to load report data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    if (fileId) {
      fetchReportData(fileId);
    } else {
      setSummaryData(null);
      setAnalysisData(null);
      setRelationshipsData(null);
      setLoading(false);
      setError("");
    }

    return () => {
      cancelled = true;
    };
  }, [fileId]);

  // Normalized clauses
  const rawClauses =
    analysisData?.analyses ||
    analysisData?.clauses ||
    analysisData?.results ||
    (Array.isArray(analysisData) ? analysisData : []) ||
    passedAnalysis?.analyses ||
    passedAnalysis?.clauses ||
    (Array.isArray(passedAnalysis) ? passedAnalysis : []);

  const clauses = Array.isArray(rawClauses) ? rawClauses : [];

  const currentSummary = summaryData?.file_id === fileId ? summaryData : null;

  const contractName =
    passedAnalysis?.filename ||
    passedAnalysis?.file_name ||
    passedAnalysis?.contract_name ||
    analysisData?.filename ||
    analysisData?.file_name ||
    analysisData?.contract_name ||
    (fileId ? `Contract (${fileId.slice(0, 8)}...)` : "No contract selected");

  const overallRisk = String(
    currentSummary?.overall_risk ||
    passedAnalysis?.overall_risk ||
    analysisData?.overall_risk ||
    "UNRATED"
  ).toUpperCase();

  const overallRiskScore = Number(
    currentSummary?.overall_risk_score ??
    passedAnalysis?.overall_risk_score ??
    analysisData?.overall_risk_score ??
    0
  );

  const riskCounts = {
    high: currentSummary?.risk_summary?.high ?? clauses.filter((c) => String(c?.risk_level || c?.risk).toUpperCase() === "HIGH").length,
    medium: currentSummary?.risk_summary?.medium ?? clauses.filter((c) => String(c?.risk_level || c?.risk).toUpperCase() === "MEDIUM").length,
    low: currentSummary?.risk_summary?.low ?? clauses.filter((c) => String(c?.risk_level || c?.risk).toUpperCase() === "LOW").length,
  };

  const totalClauses =
    currentSummary?.total_clauses ||
    clauses.length ||
    (riskCounts.high + riskCounts.medium + riskCounts.low);

  const highRiskClauses = clauses.filter(
    (c) => String(c?.risk_level || c?.risk).toUpperCase() === "HIGH"
  );

  const recommendationsList = clauses
    .filter((c) => c?.recommendation && String(c.recommendation).trim().length > 0)
    .map((c) => {
      const title = c.title || (c.clause_number ? `Clause ${c.clause_number}` : c.clause_id);
      return {
        clauseId: c.clause_id,
        clauseNumber: c.clause_number,
        title: title,
        clauseTitle: title,
        riskLevel: String(c.risk_level || "LOW").toUpperCase(),
        riskScore: c.risk_score ?? 0,
        recommendation: c.recommendation,
        whyItMatters: c.why_it_matters || null,
      };
    });

  const relationships = Array.isArray(relationshipsData?.relationships)
    ? relationshipsData.relationships
    : [];

  const relationshipTypes = relationships.reduce((acc, rel) => {
    const t = (rel.relationship_type || "REFERENCE").toUpperCase();
    acc[t] = (acc[t] || 0) + 1;
    return acc;
  }, {});

  const collectValues = (fields) => [
    ...new Set(
      clauses.flatMap((clause) =>
        fields.flatMap((field) => {
          const value = clause?.[field];
          if (Array.isArray(value)) return value;
          return value ? [value] : [];
        })
      )
    ),
  ].filter(Boolean);

  const plainSummary =
    currentSummary?.summary_points ||
    currentSummary?.summary ||
    passedAnalysis?.summary_points ||
    passedAnalysis?.summary ||
    [];

  const executiveSections = [
    {
      id: "parties",
      title: "Key Parties & Entities",
      icon: Users,
      items: collectValues([
        "parties",
        "entities",
        "persons",
        "organizations",
        "authorities",
      ]),
    },
    {
      id: "obligations",
      title: "Important Obligations",
      icon: ListChecks,
      items: [
        ...new Set([
          ...collectValues(["obligations", "duties"]),
          ...(Array.isArray(currentSummary?.key_obligations) ? currentSummary.key_obligations : []),
        ]),
      ],
    },
    {
      id: "rights",
      title: "Important Rights",
      icon: ShieldAlert,
      items: [
        ...new Set([
          ...collectValues(["rights", "permissions"]),
          ...(Array.isArray(currentSummary?.key_rights) ? currentSummary.key_rights : []),
        ]),
      ],
    },
    {
      id: "conditions",
      title: "Conditions & Exceptions",
      icon: FileText,
      items: collectValues(["conditions", "triggers", "exceptions"]),
    },
    {
      id: "financial",
      title: "Financial Terms & Penalties",
      icon: DollarSign,
      items: [
        ...new Set([
          ...collectValues([
            "monetary_terms",
            "financial_terms",
            "compensation_terms",
            "fees",
            "penalties",
            "taxes",
          ]),
          ...(Array.isArray(currentSummary?.monetary_terms) ? currentSummary.monetary_terms : []),
        ]),
      ],
    },
    {
      id: "dates",
      title: "Deadlines & Critical Dates",
      icon: CalendarDays,
      items: [
        ...new Set([
          ...collectValues(["dates", "deadlines", "durations"]),
          ...(Array.isArray(currentSummary?.deadlines) ? currentSummary.deadlines : []),
        ]),
      ],
    },
  ];

  const handleExportJson = () => {
    const reportPayload = {
      term_shield_version: "0.1.0",
      generated_at: new Date().toISOString(),
      contract_metadata: {
        id: fileId,
        filename: contractName,
        generated_date: generatedDate,
        total_clauses: totalClauses,
      },
      risk_overview: {
        overall_risk: overallRisk,
        overall_risk_score: overallRiskScore,
        high_risk_clause_count: riskCounts.high,
        medium_risk_clause_count: riskCounts.medium,
        low_risk_clause_count: riskCounts.low,
        total_clause_count: totalClauses,
      },
      executive_summary: {
        summary_points: Array.isArray(plainSummary) ? plainSummary : [plainSummary].filter(Boolean),
        parties: executiveSections.find((s) => s.id === "parties")?.items || [],
        obligations: executiveSections.find((s) => s.id === "obligations")?.items || [],
        rights: executiveSections.find((s) => s.id === "rights")?.items || [],
        conditions: executiveSections.find((s) => s.id === "conditions")?.items || [],
        financial_terms: executiveSections.find((s) => s.id === "financial")?.items || [],
        deadlines: executiveSections.find((s) => s.id === "dates")?.items || [],
      },
      high_risk_clauses: highRiskClauses.map((c) => ({
        clause_id: c.clause_id,
        clause_number: c.clause_number || null,
        title: c.title || null,
        risk_level: c.risk_level,
        risk_score: c.risk_score,
        why_it_matters: c.why_it_matters || null,
        recommendation: c.recommendation || null,
        risk_factors: c.risk_factors || [],
      })),
      recommendations: recommendationsList.map((r) => ({
        clause_id: r.clauseId,
        clause_title: r.clauseTitle,
        risk_level: r.riskLevel,
        risk_score: r.riskScore,
        recommendation: r.recommendation,
        why_it_matters: r.whyItMatters,
      })),
      relationship_summary: {
        total_relationships: relationships.length,
        relationship_types: relationshipTypes,
        relationships: relationships.map((r) => ({
          source_clause_id: r.source_clause_id,
          target_clause_id: r.target_clause_id,
          relationship_type: r.relationship_type,
          confidence: r.confidence,
          evidence: r.evidence,
        })),
      },
    };

    const blob = new Blob([JSON.stringify(reportPayload, null, 2)], {
      type: "application/json;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const downloadLink = document.createElement("a");
    const sanitizedName = contractName.replace(/[^a-zA-Z0-9_-]/g, "_");
    downloadLink.href = url;
    downloadLink.download = `TermShield_Report_${sanitizedName}_${(fileId || "").slice(0, 8)}.json`;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
    URL.revokeObjectURL(url);
  };

  const handlePrintPdf = () => {
    window.print();
  };

  if (!fileId) {
    return (
      <div className="reports-page">
        <section className="reports-empty-state">
          <div className="reports-empty-icon">
            <FileText size={28} />
          </div>
          <span className="card-label">NO CONTRACT SELECTED</span>
          <h3>Select a contract to generate report</h3>
          <p>
            Choose an analyzed contract from your library or upload a new agreement to generate an executive report with risk scoring, recommendations, and relationship summaries.
          </p>
          <div className="reports-empty-actions">
            <button
              type="button"
              className="primary-button"
              onClick={() => onNavigate && onNavigate("contracts")}
            >
              <FileText size={16} />
              <span>Browse Contract Library</span>
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => onNavigate && onNavigate("upload")}
            >
              <Upload size={16} />
              <span>Upload New Contract</span>
            </button>
          </div>
        </section>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="reports-page">
        <section className="reports-loading-state">
          <Loader2 size={32} className="spin" />
          <h3>Compiling Contract Report</h3>
          <p>Analyzing risk distributions, executive points, and clause relationships for {contractName}...</p>
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <div className="reports-page">
        <section className="reports-error-state">
          <AlertCircle size={32} />
          <h3>Report Generation Failed</h3>
          <p>{error}</p>
          <button
            type="button"
            className="primary-button"
            onClick={() => fetchReportData(fileId)}
          >
            <RefreshCw size={15} />
            <span>Retry Generating Report</span>
          </button>
        </section>
      </div>
    );
  }

  const highPct = totalClauses > 0 ? Math.round((riskCounts.high / totalClauses) * 100) : 0;
  const medPct = totalClauses > 0 ? Math.round((riskCounts.medium / totalClauses) * 100) : 0;
  const lowPct = totalClauses > 0 ? Math.max(0, 100 - highPct - medPct) : 0;

  return (
    <div className="reports-page">
      {/* 1. REPORT HEADER */}
      <section className="report-page-header">
        <div className="report-header-info">
          <div className="report-eyebrow-row">
            <span className="eyebrow">TERM SHIELD AUDIT REPORT</span>
            <span className={`report-risk-badge ${overallRisk.toLowerCase()}`}>
              {overallRisk} RISK • SCORE {overallRiskScore}/100
            </span>
          </div>

          <h1 className="report-title">{contractName}</h1>

          <div className="report-meta-pills">
            <span className="meta-pill">
              <strong>Contract ID:</strong> {fileId}
            </span>
            <span className="meta-pill">
              <strong>Generated:</strong> {generatedDate}
            </span>
            <span className="meta-pill">
              <strong>Total Clauses:</strong> {totalClauses}
            </span>
          </div>
        </div>

        <div className="report-header-actions">
          <button
            type="button"
            className="secondary-button report-action-btn"
            onClick={handleExportJson}
            title="Download report data in structured JSON format"
          >
            <Download size={15} />
            <span>Export JSON</span>
          </button>

          <button
            type="button"
            className="primary-button report-action-btn print-btn"
            onClick={handlePrintPdf}
            title="Print or save as PDF via system print dialog"
          >
            <Printer size={15} />
            <span>Print / Save PDF</span>
          </button>
        </div>
      </section>

      {/* Partial warnings if an auxiliary API failed */}
      {(summaryError || relationshipsError) && (
        <div className="report-notice-banner" role="alert">
          <AlertCircle size={16} />
          <div>
            {summaryError && <p>Note on Summary: {summaryError}</p>}
            {relationshipsError && <p>Note on Relationships: {relationshipsError}</p>}
          </div>
        </div>
      )}

      {/* 2. RISK OVERVIEW SECTION */}
      <section className="report-card report-overview-card">
        <div className="report-card-heading">
          <div className="report-card-icon risk">
            <ShieldAlert size={18} />
          </div>
          <div>
            <span className="card-label">RISK PROFILE</span>
            <h3>Risk Assessment &amp; Clause Distribution</h3>
          </div>
        </div>

        <div className="risk-overview-grid">
          <div className="risk-score-box">
            <span className="score-num">{overallRiskScore}</span>
            <span className="score-denom">/ 100</span>
            <span className={`risk-tag-large ${overallRisk.toLowerCase()}`}>{overallRisk} RISK</span>
            <span className="score-desc">Calculated based on weighted severity across all evaluated clauses.</span>
          </div>

          <div className="risk-breakdown-box">
            <div className="risk-stat-pills">
              <div className="risk-stat-pill high">
                <span className="pill-count">{riskCounts.high}</span>
                <span className="pill-label">High Risk</span>
              </div>
              <div className="risk-stat-pill medium">
                <span className="pill-count">{riskCounts.medium}</span>
                <span className="pill-label">Medium Risk</span>
              </div>
              <div className="risk-stat-pill low">
                <span className="pill-count">{riskCounts.low}</span>
                <span className="pill-label">Low Risk</span>
              </div>
              <div className="risk-stat-pill total">
                <span className="pill-count">{totalClauses}</span>
                <span className="pill-label">Total Evaluated</span>
              </div>
            </div>

            <div className="risk-bar-container">
              <div className="risk-bar-label-row">
                <span>Distribution Breakdown</span>
                <span>{highPct}% High • {medPct}% Med • {lowPct}% Low</span>
              </div>
              <div className="risk-bar-track">
                <div className="risk-bar-fill high" style={{ width: `${highPct}%` }} title={`High risk: ${highPct}%`} />
                <div className="risk-bar-fill medium" style={{ width: `${medPct}%` }} title={`Medium risk: ${medPct}%`} />
                <div className="risk-bar-fill low" style={{ width: `${lowPct}%` }} title={`Low risk: ${lowPct}%`} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. EXECUTIVE SUMMARY SECTION */}
      <section className="report-card report-executive-card">
        <div className="report-card-heading">
          <div className="report-card-icon summary">
            <Sparkles size={18} />
          </div>
          <div>
            <span className="card-label">PLAIN-LANGUAGE SYNTHESIS</span>
            <h3>Executive Summary</h3>
          </div>
        </div>

        <div className="executive-summary-body">
          {plainSummary?.length ? (
            Array.isArray(plainSummary) ? (
              <ul className="executive-points-list">
                {plainSummary.map((point, index) => (
                  <li key={index}>{point}</li>
                ))}
              </ul>
            ) : (
              <p className="executive-paragraph">{plainSummary}</p>
            )
          ) : (
            <p className="summary-unavailable">A plain-language summary was not generated for this contract.</p>
          )}
        </div>

        <div className="report-sections-grid">
          {executiveSections.map((sec) => (
            <ReportSectionItem key={sec.id} {...sec} />
          ))}
        </div>
      </section>

      {/* 4. HIGH-RISK CLAUSES SECTION */}
      <section className="report-card report-high-risk-card">
        <div className="report-card-heading">
          <div className="report-card-icon high-risk">
            <ShieldAlert size={18} />
          </div>
          <div>
            <span className="card-label">PRIORITY ATTENTION</span>
            <h3>High-Risk Clauses ({highRiskClauses.length})</h3>
          </div>
        </div>

        {highRiskClauses.length > 0 ? (
          <div className="high-risk-clauses-list">
            {highRiskClauses.map((clause, idx) => {
              const displayTitle =
                clause.title ||
                (clause.clause_number ? `Clause ${clause.clause_number}` : `Clause ${idx + 1}`);

              return (
                <div key={clause.clause_id || idx} className="high-risk-clause-row">
                  <div className="clause-row-header">
                    <div className="clause-row-title-wrap">
                      <span className="clause-badge high">HIGH RISK</span>
                      <h4>{displayTitle}</h4>
                      {clause.clause_type && (
                        <span className="clause-type-tag">{clause.clause_type}</span>
                      )}
                    </div>
                    <span className="clause-score-pill">Score {clause.risk_score ?? 0}/100</span>
                  </div>

                  {clause.why_it_matters && (
                    <div className="clause-callout why-matters">
                      <strong>Why It Matters:</strong>
                      <p>{clause.why_it_matters}</p>
                    </div>
                  )}

                  {clause.recommendation && (
                    <div className="clause-callout recommendation">
                      <strong>Recommendation:</strong>
                      <p>{clause.recommendation}</p>
                    </div>
                  )}

                  {Array.isArray(clause.risk_factors) && clause.risk_factors.length > 0 && (
                    <div className="clause-factors-row">
                      <span className="factors-label">Risk Factors:</span>
                      {clause.risk_factors.map((f, fIdx) => (
                        <span key={fIdx} className="factor-tag">
                          {f}
                        </span>
                      ))}
                    </div>
                  )}

                  {clause.text && (
                    <div className="clause-excerpt-box">
                      <span className="excerpt-label">Clause Excerpt:</span>
                      <p className="excerpt-text">&ldquo;{clause.text.slice(0, 320)}{clause.text.length > 320 ? "..." : ""}&rdquo;</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="report-zero-state">
            <CheckCircle2 size={24} className="success-icon" />
            <h4>No High-Risk Clauses Detected</h4>
            <p>None of the segmented clauses in this contract crossed the high-risk threshold.</p>
          </div>
        )}
      </section>

      {/* 5. RECOMMENDATIONS SECTION */}
      <section className="report-card report-recommendations-card">
        <div className="report-card-heading">
          <div className="report-card-icon rec">
            <ListChecks size={18} />
          </div>
          <div>
            <span className="card-label">ACTIONABLE ADVICE</span>
            <h3>Contract Recommendations ({recommendationsList.length})</h3>
          </div>
        </div>

        {recommendationsList.length > 0 ? (
          <div className="recommendations-list">
            {recommendationsList.map((rec, idx) => (
              <div key={rec.clauseId || idx} className="recommendation-item">
                <div className="rec-item-header">
                  <span className={`rec-risk-tag ${rec.riskLevel.toLowerCase()}`}>
                    {rec.riskLevel}
                  </span>
                  <strong>{rec.clauseTitle}</strong>
                </div>

                <div className="rec-item-body">
                  <p className="rec-text">{rec.recommendation}</p>
                  {rec.whyItMatters && (
                    <p className="rec-context">
                      <span>Context:</span> {rec.whyItMatters}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="report-zero-state">
            <CheckCircle2 size={24} className="success-icon" />
            <h4>No Specific Recommendations</h4>
            <p>No actionable recommendations were generated for this agreement based on current analysis findings.</p>
          </div>
        )}
      </section>

      {/* 6. CLAUSE RELATIONSHIP SUMMARY */}
      <section className="report-card report-relationships-card">
        <div className="report-card-heading">
          <div className="report-card-icon rel">
            <Network size={18} />
          </div>
          <div>
            <span className="card-label">INTER-CLAUSE DYNAMICS</span>
            <h3>Clause Relationships &amp; Dependencies ({relationships.length})</h3>
          </div>
        </div>

        {relationships.length > 0 ? (
          <>
            <div className="relationship-types-row">
              {Object.entries(relationshipTypes).map(([type, count]) => (
                <span key={type} className="rel-type-count-pill">
                  <strong>{type}</strong>
                  <span className="count-num">{count}</span>
                </span>
              ))}
            </div>

            <div className="relationships-summary-list">
              {relationships.map((rel, idx) => (
                <div key={idx} className="rel-summary-row">
                  <div className="rel-summary-flow">
                    <span className="rel-clause-id">{rel.source_clause_id}</span>
                    <ArrowRight size={13} className="rel-arrow" />
                    <span className="rel-clause-id">{rel.target_clause_id || "Agreement Scope"}</span>
                    <span className="rel-type-badge">{rel.relationship_type}</span>
                    <span className="rel-conf-pill">{Math.round((rel.confidence ?? 1.0) * 100)}% confidence</span>
                  </div>

                  {rel.evidence && (
                    <p className="rel-evidence-snippet">&ldquo;{rel.evidence}&rdquo;</p>
                  )}
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="report-zero-state">
            <FileText size={24} className="muted-icon" />
            <h4>No Cross-Clause Dependencies Found</h4>
            <p>No cross-referencing or modifying relationships between clauses were identified in this document.</p>
          </div>
        )}
      </section>
    </div>
  );
}

function ReportSectionItem({ title, icon: Icon, items }) {
  return (
    <div className="report-section-item">
      <div className="report-section-item-header">
        <div className="report-section-mini-icon">
          <Icon size={14} />
        </div>
        <h4>{title}</h4>
      </div>

      {items && items.length > 0 ? (
        <ul className="report-section-list">
          {items.map((it, idx) => (
            <li key={idx}>{it}</li>
          ))}
        </ul>
      ) : (
        <span className="report-section-none">None detected</span>
      )}
    </div>
  );
}

const ContractSummary = ReportsPage;

/* =========================
   ASK MY T&C
========================= */

function formatInlineText(str) {
  if (!str) return "";

  const parts = str.split(/(\*\*.*?\*\*)/g);
  if (parts.length > 1) {
    return (
      <>
        {parts.map((part, i) => {
          if (part.startsWith("**") && part.endsWith("**")) {
            return (
              <strong key={i} className="ask-highlight-label">
                {part.slice(2, -2)}
              </strong>
            );
          }
          return part;
        })}
      </>
    );
  }

  const labelMatch = str.match(/^([A-Za-z0-9\s()_-]{2,30}:)(.*)$/);
  if (labelMatch) {
    return (
      <>
        <strong className="ask-highlight-label">{labelMatch[1]}</strong>
        {labelMatch[2]}
      </>
    );
  }

  return str;
}

function renderAssistantContent(text) {
  if (!text || typeof text !== "string") return null;

  const rawLines = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  if (rawLines.length === 0) return null;

  const hasBullets = rawLines.some((l) => /^[-*•]\s+|\d+\.\s+/.test(l));

  if (!hasBullets) {
    return (
      <div className="ask-assistant-body">
        {rawLines.map((line, idx) => (
          <p key={idx} className="ask-assistant-paragraph">
            {formatInlineText(line)}
          </p>
        ))}
      </div>
    );
  }

  const elements = [];
  let currentList = [];

  const flushList = (key) => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={key} className="ask-assistant-list">
          {currentList.map((item, i) => (
            <li key={i} className="ask-assistant-list-item">
              <span className="ask-bullet-dot" aria-hidden="true" />
              <div className="ask-item-text">{formatInlineText(item)}</div>
            </li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  rawLines.forEach((line, idx) => {
    const bulletMatch =
      line.match(/^[-*•]\s+(.*)$/) || line.match(/^\d+\.\s+(.*)$/);

    if (bulletMatch) {
      currentList.push(bulletMatch[1]);
    } else {
      flushList(`list-before-${idx}`);
      elements.push(
        <p key={`p-${idx}`} className="ask-assistant-paragraph ask-lead-text">
          {formatInlineText(line)}
        </p>
      );
    }
  });

  flushList("list-final");

  return <div className="ask-assistant-body">{elements}</div>;
}

function AskMyTC({ fileId, analysis }) {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState([]);
  const [isAsking, setIsAsking] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [qaError, setQaError] = useState("");
  const messagesEndRef = useRef(null);

  const hasContract = Boolean(fileId);
  const contractName =
    analysis?.filename ||
    analysis?.file_name ||
    analysis?.contract_name ||
    "Selected contract";

  const suggestedQuestions = [
    "What are my biggest obligations?",
    "Which clauses carry the most risk?",
    "What should I review before signing?",
  ];

  const fetchHistory = async (targetFileId) => {
    if (!targetFileId) {
      setMessages([]);
      setHistoryLoading(false);
      setHistoryError("");
      return;
    }

    setMessages([]);
    setHistoryLoading(true);
    setHistoryError("");
    setQaError("");

    try {
      const data = await getQAHistory(targetFileId);
      const formatted = [];
      if (Array.isArray(data)) {
        data.forEach((record) => {
          if (record.question) {
            formatted.push({
              id: `${record.id}-user`,
              role: "user",
              text: record.question,
              createdAt: record.created_at,
            });
          }
          if (record.answer) {
            formatted.push({
              id: `${record.id}-assistant`,
              role: "assistant",
              text: record.answer,
              createdAt: record.created_at,
            });
          }
        });
      }
      setMessages(formatted);
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "Failed to load conversation history.";
      setHistoryError(message);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory(fileId);
  }, [fileId]);

  useEffect(() => {
    if (messages.length > 0 || isAsking) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isAsking]);

  const handleSend = async () => {
    const question = draft.trim();
    if (!question || !hasContract || isAsking || historyLoading) return;

    const tempId = Date.now();
    setMessages((currentMessages) => [
      ...currentMessages,
      { id: `${tempId}-user`, role: "user", text: question },
    ]);
    setDraft("");
    setQaError("");
    setIsAsking(true);

    try {
      const response = await askContractQuestion(
        fileId,
        question
      );

      if (!response?.answer) {
        throw new Error(
          "The QA service returned no answer."
        );
      }

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          text: response.answer,
        },
      ]);
    } catch (error) {
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        "Unable to get an answer from the contract assistant.";

      setQaError(message);
    } finally {
      setIsAsking(false);
    }
  };

  const handleInputKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="ask-page">
      <section className="ask-page-header">
        <div>
          <span className="eyebrow">CONTRACT ASSISTANT</span>
          <h2>Ask My T&C</h2>
          <p>
            Ask focused questions about the language, obligations, and risk
            signals in your selected contract.
          </p>
        </div>

        <div className={`ask-context-indicator ${hasContract ? "ready" : "empty"}`}>
          <span className="ask-context-dot" />
          <div>
            <span>ACTIVE CONTEXT</span>
            <strong>{hasContract ? contractName : "No contract selected"}</strong>
          </div>
        </div>
      </section>

      <section className="ask-chat-shell">
        <div className="ask-chat-header">
          <div className="ask-assistant-avatar">
            <Bot size={19} />
          </div>
          <div>
            <strong>Term Shield assistant</strong>
            <span>
              {hasContract
                ? historyLoading
                  ? "Loading conversation history..."
                  : "Contract context ready"
                : "Waiting for a contract"}
            </span>
          </div>
          <span className="ask-chat-status">
            <span />
            QA connected
          </span>
        </div>

        <div className="ask-chat-messages" aria-live="polite">
          <div className="ask-message assistant-message">
            <div className="ask-message-avatar">
              <Bot size={15} />
            </div>
            <div className="ask-message-content">
              <span className="ask-message-author">Term Shield</span>
              <div className="ask-message-bubble">
                {renderAssistantContent(
                  hasContract
                    ? `I’m ready to help you understand ${contractName}. Ask about a clause, obligation, deadline, or risk signal.`
                    : "Upload and analyze a contract first, then I can help you explore its terms in plain language."
                )}
              </div>
            </div>
          </div>

          {historyLoading && (
            <div className="ask-history-loading">
              <Loader2 size={16} className="spin" />
              <span>Loading saved conversation history...</span>
            </div>
          )}

          {historyError && !historyLoading && (
            <div className="ask-history-error-banner" role="alert">
              <div className="ask-history-error-text">
                <AlertCircle size={15} />
                <span>{historyError}</span>
              </div>
              <button
                type="button"
                className="ask-history-retry-btn"
                onClick={() => fetchHistory(fileId)}
              >
                <RefreshCw size={13} />
                <span>Retry</span>
              </button>
            </div>
          )}

          {messages.map((message) => (
            <div
              className={`ask-message ${message.role === "assistant" ? "assistant-message" : "user-message"}`}
              key={message.id}
            >
              {message.role === "assistant" && (
                <div className="ask-message-avatar">
                  <Bot size={15} />
                </div>
              )}
              <div className="ask-message-content">
                <span className="ask-message-author">
                  {message.role === "assistant" ? "Term Shield" : "You"}
                </span>
                <div className="ask-message-bubble">
                  {message.role === "assistant"
                    ? renderAssistantContent(message.text)
                    : message.text}
                </div>
              </div>
            </div>
          ))}

          {isAsking && (
            <div className="ask-message assistant-message">
              <div className="ask-message-avatar">
                <Bot size={15} />
              </div>
              <div className="ask-message-content">
                <span className="ask-message-author">Term Shield</span>
                <div className="ask-message-bubble ask-thinking-bubble">
                  <Loader2 size={15} className="spin" />
                  Thinking about your contract...
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="ask-chat-composer">
          <div className="ask-suggestions">
            <span>Try asking</span>
            <div>
              {suggestedQuestions.map((question) => (
                <button
                  type="button"
                  key={question}
                  disabled={!hasContract || isAsking || historyLoading}
                  onClick={() => setDraft(question)}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>

          <div className="ask-input-row">
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleInputKeyDown}
              disabled={!hasContract || isAsking || historyLoading}
              placeholder={
                hasContract
                  ? "Ask about this contract..."
                  : "Select a contract to start asking questions"
              }
              rows={1}
              aria-label="Ask about the selected contract"
            />
            <button
              className="ask-send-button"
              type="button"
              disabled={!hasContract || !draft.trim() || isAsking || historyLoading}
              onClick={handleSend}
              aria-label="Send question"
            >
              <Send size={17} />
            </button>
          </div>

          {qaError && (
            <div className="ask-qa-error" role="alert">
              <AlertCircle size={14} />
              <span>{qaError}</span>
            </div>
          )}

          <p className="ask-composer-note">
            Answers are grounded in the selected contract and persisted to your library.
          </p>
        </div>
      </section>
    </div>
  );
}


/* =========================
   DASHBOARD
========================= */

function Dashboard({
  onNavigate,
  fileId,
  analysis,
  contracts = [],
  contractsLoading = false,
  contractsError = "",
  onRefresh,
  onSelectContract,
  currentUser,
}) {
  const hour = new Date().getHours();
  const timeGreeting =
    hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const firstName = currentUser?.full_name?.trim()
    ? currentUser.full_name.trim().split(/\s+/)[0]
    : currentUser?.email
      ? currentUser.email.split("@")[0]
      : "";

  const totalContracts = contracts.length;

  const highRiskContracts = contracts.filter((c) => {
    const r = String(c?.overall_risk || "").toLowerCase();
    return r === "high";
  });

  const medRiskContracts = contracts.filter((c) => {
    const r = String(c?.overall_risk || "").toLowerCase();
    return r === "medium" || r === "med";
  });

  const lowRiskContracts = contracts.filter((c) => {
    const r = String(c?.overall_risk || "").toLowerCase();
    return r === "low";
  });

  const scoredContracts = contracts.filter(
    (c) => typeof c?.overall_risk_score === "number" && c.overall_risk_score >= 0
  );

  const avgRiskScore =
    scoredContracts.length > 0
      ? Math.round(
        scoredContracts.reduce((acc, c) => acc + c.overall_risk_score, 0) /
        scoredContracts.length
      )
      : null;

  const analyzedContracts = contracts.filter((c) => {
    const status = String(c?.status || "").toLowerCase();
    return (
      status === "analyzed" ||
      status === "ready" ||
      Boolean(c?.overall_risk) ||
      (typeof c?.overall_risk_score === "number" && c.overall_risk_score > 0)
    );
  }).length;

  const ratedCount =
    highRiskContracts.length + medRiskContracts.length + lowRiskContracts.length;
  const riskBase = ratedCount > 0 ? ratedCount : 1;
  const highPct =
    ratedCount > 0 ? Math.round((highRiskContracts.length / riskBase) * 100) : 0;
  const medPct =
    ratedCount > 0 ? Math.round((medRiskContracts.length / riskBase) * 100) : 0;
  const lowPct = ratedCount > 0 ? Math.max(0, 100 - highPct - medPct) : 0;

  const recentContracts = contracts.slice(0, 5);

  const attentionContracts = [...highRiskContracts].sort(
    (a, b) => (b.overall_risk_score || 0) - (a.overall_risk_score || 0)
  );

  const chronologicalContracts = [...scoredContracts].sort((a, b) => {
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    return timeA - timeB;
  });

  const hasTrend = chronologicalContracts.length >= 2;
  const latestScored = hasTrend
    ? chronologicalContracts[chronologicalContracts.length - 1]
    : null;
  const previousScored = hasTrend
    ? chronologicalContracts.slice(0, chronologicalContracts.length - 1)
    : [];
  const previousAvgScore =
    previousScored.length > 0
      ? Math.round(
        previousScored.reduce((acc, c) => acc + (c.overall_risk_score || 0), 0) /
        previousScored.length
      )
      : null;

  const formatContractDate = (dateStr) => {
    if (!dateStr) return "Unknown date";
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return "Unknown date";
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return "Unknown date";
    }
  };

  const handleContractClick = (contractId) => {
    if (onSelectContract) {
      onSelectContract(contractId);
    } else {
      onNavigate("contracts");
    }
  };

  if (contractsLoading && totalContracts === 0) {
    return (
      <div className="dashboard">
        <section className="dashboard-loading-state">
          <Loader2 size={36} className="spin" />
          <h3>Synchronizing Workspace Dashboard</h3>
          <p>Connecting to your Term Shield library to compile intelligence and risk posture...</p>
        </section>
      </div>
    );
  }

  if (contractsError && totalContracts === 0) {
    return (
      <div className="dashboard">
        <section className="dashboard-error-state">
          <AlertCircle size={36} />
          <h3>Unable to Load Contract Library</h3>
          <p>{contractsError}</p>
          <div className="dashboard-error-actions">
            <button
              type="button"
              className="primary-button"
              onClick={() => onRefresh && onRefresh()}
            >
              <RefreshCw size={15} />
              <span>Retry Connection</span>
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => onNavigate("upload")}
            >
              <Upload size={15} />
              <span>Upload Contract</span>
            </button>
          </div>
        </section>
      </div>
    );
  }

  if (!contractsLoading && !contractsError && totalContracts === 0) {
    return (
      <div className="dashboard">
        <section className="welcome-section">
          <div className="welcome-copy">
            <span className="eyebrow">WORKSPACE INTELLIGENCE</span>
            <h2>
              Good to see you{firstName ? `, ${firstName}` : ""}.
              <br />
              <span>Make every contract clearer.</span>
            </h2>
            <p>
              Your contract workspace at a glance. Review risk, track important terms,
              and turn dense legal agreements into decisions you can act on.
            </p>
          </div>

          <div className="welcome-actions">
            <span className="workspace-status">
              <span className="status-dot" />
              Workspace ready (0 contracts)
            </span>
            <div className="dashboard-header-buttons">
              <button
                type="button"
                className="secondary-button dashboard-refresh-btn"
                onClick={() => onRefresh && onRefresh()}
                title="Refresh workspace library"
              >
                <RefreshCw size={15} />
                <span>Refresh</span>
              </button>
              <button
                className="primary-button"
                type="button"
                onClick={() => onNavigate("upload")}
              >
                <Upload size={17} />
                <span>Upload contract</span>
              </button>
            </div>
          </div>
        </section>

        <section className="dashboard-empty-card">
          <div className="empty-icon-wrap">
            <FileText size={32} />
          </div>
          <h3>Your contract library is empty</h3>
          <p>
            Upload agreements, licenses, or terms to automatically detect clauses, evaluate risks,
            and generate plain-language executive reports.
          </p>
          <div className="dashboard-empty-actions">
            <button
              className="primary-button"
              type="button"
              onClick={() => onNavigate("upload")}
            >
              <Upload size={16} />
              <span>Upload Your First Contract</span>
            </button>
          </div>

          <div className="empty-guide-grid">
            <div className="empty-guide-step">
              <div className="step-num">1</div>
              <strong>Document Ingestion</strong>
              <span>PDF, DOCX, TXT, OCR images, audio/video recordings, and web URLs.</span>
            </div>
            <div className="empty-guide-step">
              <div className="step-num">2</div>
              <strong>AI Risk Analysis</strong>
              <span>Automated classification, risk factor detection, and obligation tagging.</span>
            </div>
            <div className="empty-guide-step">
              <div className="step-num">3</div>
              <strong>Decision Intelligence</strong>
              <span>Executive reports, clause relationship graph, and Ask My T&amp;C Q&amp;A.</span>
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* 1. DASHBOARD HEADER */}
      <section className="welcome-section">
        <div className="welcome-copy">
          <span className="eyebrow">AI CONTRACT INTELLIGENCE</span>
          <h2>
            Good to see you{firstName ? `, ${firstName}` : ""}.
            <br />
            <span>Workspace contract intelligence.</span>
          </h2>
          <p>
            Workspace-wide overview of your contracts, risk distributions, actionable flags,
            and recent legal agreements in one clear view.
          </p>
        </div>

        <div className="welcome-actions">
          <span className="workspace-status">
            <span className="status-dot" />
            Workspace active • {totalContracts} contract{totalContracts === 1 ? "" : "s"}
          </span>

          <div className="dashboard-header-buttons">
            <button
              type="button"
              className="secondary-button dashboard-refresh-btn"
              onClick={() => onRefresh && onRefresh()}
              title="Refresh workspace contracts"
            >
              <RefreshCw size={15} className={contractsLoading ? "spin" : ""} />
              <span>Refresh</span>
            </button>
            <button
              className="primary-button"
              type="button"
              onClick={() => onNavigate("upload")}
            >
              <Upload size={17} />
              <span>Upload contract</span>
            </button>
          </div>
        </div>
      </section>

      {/* 2. WORKSPACE METRICS */}
      <section className="stats-grid workspace-stats-grid">
        <StatCard
          label="Total Contracts"
          value={totalContracts}
          detail="In workspace library"
          icon={FileText}
        />
        <StatCard
          label="Contracts Analyzed"
          value={analyzedContracts}
          detail={
            totalContracts > 0
              ? `${Math.round((analyzedContracts / totalContracts) * 100)}% analyzed`
              : "Awaiting analysis"
          }
          icon={ShieldCheck}
        />
        <StatCard
          label="Average Risk Score"
          value={avgRiskScore !== null ? `${avgRiskScore}/100` : "N/A"}
          detail={
            avgRiskScore !== null
              ? avgRiskScore >= 70
                ? "High risk baseline"
                : avgRiskScore >= 40
                  ? "Moderate risk baseline"
                  : "Low risk baseline"
              : "No scored contracts"
          }
          icon={BarChart3}
        />
        <StatCard
          label="High-Risk Contracts"
          value={highRiskContracts.length}
          detail={highRiskContracts.length ? "Requires immediate review" : "None detected"}
          icon={ShieldAlert}
          danger={highRiskContracts.length > 0}
        />
        <StatCard
          label="Medium-Risk"
          value={medRiskContracts.length}
          detail="Moderate review priority"
          icon={ListChecks}
        />
        <StatCard
          label="Low-Risk"
          value={lowRiskContracts.length}
          detail="Standard compliance"
          icon={CheckCircle2}
        />
      </section>

      {/* 3. PRIMARY GRID: RISK DISTRIBUTION & REQUIRES ATTENTION */}
      <section className="dashboard-grid dashboard-primary-grid">
        {/* RISK DISTRIBUTION */}
        <div className="dashboard-card risk-overview-card">
          <div className="card-heading">
            <div>
              <span className="card-label">RISK DISTRIBUTION</span>
              <h3>Portfolio Risk Posture</h3>
            </div>
            <div className="card-icon purple">
              <ShieldAlert size={19} />
            </div>
          </div>

          <div className="risk-meter" aria-label="Risk distribution">
            <span
              className="risk-meter-high"
              style={{ width: `${highPct}%` }}
              title={`High Risk: ${highRiskContracts.length} (${highPct}%)`}
            />
            <span
              className="risk-meter-medium"
              style={{ width: `${medPct}%` }}
              title={`Medium Risk: ${medRiskContracts.length} (${medPct}%)`}
            />
            <span
              className="risk-meter-low"
              style={{ width: `${lowPct}%` }}
              title={`Low Risk: ${lowRiskContracts.length} (${lowPct}%)`}
            />
          </div>

          <div className="risk-summary">
            <div>
              <strong>{highRiskContracts.length}</strong>
              <span>High risk ({highPct}%)</span>
            </div>
            <div>
              <strong>{medRiskContracts.length}</strong>
              <span>Medium risk ({medPct}%)</span>
            </div>
            <div>
              <strong>{lowRiskContracts.length}</strong>
              <span>Low risk ({lowPct}%)</span>
            </div>
          </div>

          <div className="portfolio-posture-badge">
            <span className="posture-label">Health Assessment:</span>
            <strong className={avgRiskScore !== null && avgRiskScore >= 70 ? "high" : avgRiskScore !== null && avgRiskScore >= 40 ? "medium" : "low"}>
              {avgRiskScore !== null
                ? avgRiskScore >= 70
                  ? "Elevated Risk Portfolio"
                  : avgRiskScore >= 40
                    ? "Moderate Risk Portfolio"
                    : "Safe / Low Risk Portfolio"
                : "Awaiting Risk Evaluation"}
            </strong>
          </div>

          <button
            className="text-button risk-link"
            type="button"
            onClick={() => onNavigate("contracts")}
          >
            View all contracts in library →
          </button>
        </div>

        {/* 5. REQUIRES ATTENTION SECTION */}
        <div className="dashboard-card requires-attention-card">
          <div className="card-heading">
            <div>
              <span className="card-label">HIGH-RISK OVERSIGHT</span>
              <h3>Requires Attention ({highRiskContracts.length})</h3>
            </div>
            <div className="card-icon danger">
              <ShieldAlert size={19} />
            </div>
          </div>

          {attentionContracts.length > 0 ? (
            <div className="attention-list">
              {attentionContracts.slice(0, 4).map((contract) => (
                <div
                  key={contract.id}
                  className="attention-contract-row"
                  onClick={() => handleContractClick(contract.id)}
                  title="Click to view full analysis"
                >
                  <div className="attention-row-main">
                    <strong>{contract.filename}</strong>
                    <div className="attention-row-meta">
                      <span className="attention-date">{formatContractDate(contract.created_at)}</span>
                      <span className="attention-type">{contract.file_type?.toUpperCase() || "DOC"}</span>
                    </div>
                  </div>

                  <div className="attention-row-right">
                    <span className="clause-badge high">HIGH RISK</span>
                    <span className="attention-score-pill">
                      Score {contract.overall_risk_score ?? 0}/100
                    </span>
                    <button
                      type="button"
                      className="attention-action-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleContractClick(contract.id);
                      }}
                    >
                      Inspect →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="attention-empty-state">
              <div className="attention-empty-icon">
                <ShieldCheck size={24} />
              </div>
              <h4>All Clear: No High-Risk Contracts</h4>
              <p>
                Every analyzed contract in your workspace is currently within low or moderate risk parameters.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* 6. RISK TREND / INSIGHT (if >= 2 scored contracts) */}
      {hasTrend && (
        <section className="dashboard-card risk-trend-card">
          <div className="card-heading">
            <div>
              <span className="card-label">CHRONOLOGICAL INTELLIGENCE</span>
              <h3>Risk Trend Across Additions</h3>
            </div>
            <div className="card-icon purple">
              <TrendingUp size={19} />
            </div>
          </div>

          <div className="trend-summary-note">
            <Clock size={15} />
            <span>
              {latestScored && previousAvgScore !== null
                ? latestScored.overall_risk_score < previousAvgScore
                  ? `Recent addition (${latestScored.filename}) lowered portfolio risk: scored ${latestScored.overall_risk_score}/100 vs previous average of ${previousAvgScore}/100.`
                  : latestScored.overall_risk_score > previousAvgScore
                    ? `Recent addition (${latestScored.filename}) introduced higher risk: scored ${latestScored.overall_risk_score}/100 vs previous average of ${previousAvgScore}/100.`
                    : `Recent addition (${latestScored.filename}) matched baseline risk at ${latestScored.overall_risk_score}/100.`
                : "Tracking chronological contract evaluations."}
            </span>
          </div>

          <div className="risk-trend-timeline">
            {chronologicalContracts.map((c, idx) => {
              const riskLvl = String(c.overall_risk || "unrated").toLowerCase();
              return (
                <div
                  key={c.id || idx}
                  className="risk-trend-point"
                  onClick={() => handleContractClick(c.id)}
                  title={`View analysis for ${c.filename}`}
                >
                  <div className="trend-point-header">
                    <span className="trend-seq">#{idx + 1}</span>
                    <span className="trend-date">{formatContractDate(c.created_at)}</span>
                  </div>
                  <strong className="trend-filename">{c.filename}</strong>
                  <div className="trend-point-footer">
                    <span className={`trend-risk-tag ${riskLvl}`}>
                      {c.overall_risk || "UNRATED"}
                    </span>
                    <span className="trend-score">
                      {c.overall_risk_score ?? "--"}/100
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* 4. RECENT CONTRACTS */}
      <section className="dashboard-card recent-panel">
        <div className="card-heading">
          <div>
            <span className="card-label">CONTRACT LIBRARY</span>
            <h3>Recent Contracts ({totalContracts})</h3>
          </div>

          <button
            className="text-button"
            type="button"
            onClick={() => onNavigate("contracts")}
          >
            View all contracts ({totalContracts}) →
          </button>
        </div>

        {recentContracts.length > 0 ? (
          <div className="recent-contracts-list">
            {recentContracts.map((contract) => {
              const riskStr = String(contract.overall_risk || "unrated").toLowerCase();
              return (
                <div
                  key={contract.id}
                  className="recent-contract-row clickable-row"
                  onClick={() => handleContractClick(contract.id)}
                >
                  <div className="recent-contract-icon">
                    <FileText size={20} />
                  </div>

                  <div className="recent-contract-info">
                    <strong>{contract.filename}</strong>
                    <span>
                      Added {formatContractDate(contract.created_at)} •{" "}
                      {contract.file_type?.toUpperCase() || "DOCUMENT"} • ID: {contract.id}
                    </span>
                  </div>

                  <div className="recent-contract-badges">
                    <span className={`recent-risk-badge ${riskStr}`}>
                      {contract.overall_risk || "UNRATED"}
                    </span>
                    {typeof contract.overall_risk_score === "number" && (
                      <span className="recent-score-pill">
                        Score {contract.overall_risk_score}/100
                      </span>
                    )}
                    <span className="contract-status">
                      <CheckCircle2 size={13} />
                      {contract.status || "Ready"}
                    </span>
                  </div>

                  <button
                    className="secondary-button recent-action"
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleContractClick(contract.id);
                    }}
                  >
                    View analysis →
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-icon">
              <FileText size={23} />
            </div>
            <h4>Your contract library is ready</h4>
            <p>Upload your first contract to see its clauses, risks, obligations and AI insights here.</p>
            <button
              className="secondary-button"
              type="button"
              onClick={() => onNavigate("upload")}
            >
              <Upload size={15} />
              <span>Upload your first contract</span>
            </button>
          </div>
        )}
      </section>
    </div>
  );
}

/* =========================
   UPLOAD CONTRACT
========================= */

function UploadContract({
  onBack,
  onAnalysisComplete,
}) {
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [url, setUrl] = useState("");
  const [activeInput, setActiveInput] = useState("file");
  const [dragging, setDragging] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState("");
  const isUrlReady = url.trim().length > 0;

  const uploadStatus = uploading
    ? "uploading"
    : uploadError
      ? "error"
      : uploadResult
        ? "success"
        : selectedFile || isUrlReady
          ? "selected"
          : "idle";

  const selectFile = (file) => {
    if (!file) return;

    setSelectedFile(file);
    setActiveInput("file");
    setUploadResult(null);
    setUploadError("");
  };

  const handleFileChange = (event) => {
    selectFile(event.target.files?.[0]);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);

    const file = event.dataTransfer.files?.[0];

    selectFile(file);
  };

  const removeFile = () => {
    setSelectedFile(null);
    setUploadResult(null);
    setUploadError("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  /* =========================
     REAL BACKEND ANALYSIS
  ========================= */

  const handleAnalyze = async () => {
    if ((!selectedFile && !isUrlReady) || uploading) return;

    setUploading(true);
    setUploadError("");
    setUploadResult(null);

    try {
      // 1. Upload the selected source using the existing API helpers.
      let uploadResponse;

      if (activeInput === "url") {
        uploadResponse = await ingestContractUrl(url.trim());
      } else if (selectedFile.type.startsWith("audio/")) {
        uploadResponse = await uploadContractAudio(selectedFile);
      } else if (selectedFile.type.startsWith("video/")) {
        uploadResponse = await uploadContractVideo(selectedFile);
      } else {
        uploadResponse = await uploadContractFile(selectedFile);
      }

      setUploadResult(uploadResponse);

      const fileId = uploadResponse.file_id;

      if (!fileId) {
        throw new Error(
          "The backend did not return a file ID."
        );
      }

      // 2. Fetch AI clause analysis
      const analysisResponse =
        await getContractAnalysis(fileId);

      console.log(
        "Contract upload response:",
        uploadResponse
      );

      console.log(
        "Contract analysis response:",
        analysisResponse
      );

      // 3. Store the result in App state
      onAnalysisComplete(
        fileId,
        analysisResponse
      );
    } catch (error) {
      console.error(
        "Contract analysis failed:",
        error
      );

      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        "Unable to analyze the contract.";

      setUploadError(message);
    } finally {
      setUploading(false);
    }
  };

  const canAnalyze =
    activeInput === "url" ? isUrlReady : Boolean(selectedFile);

  return (
    <div className="upload-page">
      <button
        className="back-button"
        type="button"
        onClick={onBack}
      >
        <ArrowLeft size={16} />
        Back to dashboard
      </button>

      <section className="upload-header">
        <div>
          <span className="eyebrow">NEW ANALYSIS</span>

          <h2>Analyze a contract</h2>

          <p>
            Give Term Shield your contract and we'll turn
            complex legal language into clear, actionable
            insights.
          </p>
        </div>

        <div className="upload-status-strip" aria-live="polite">
          <span className={`status-marker ${uploadStatus}`} />
          <span>
            {uploadStatus === "idle" && "Ready for a secure intake"}
            {uploadStatus === "selected" && "Source selected and ready"}
            {uploadStatus === "uploading" && "Uploading and analyzing securely"}
            {uploadStatus === "success" && "Analysis ready"}
            {uploadStatus === "error" && "Action needs attention"}
          </span>
        </div>
      </section>

      <div className="upload-methods">
        <button
          type="button"
          className={`method-tab ${activeInput === "file" ? "active" : ""
            }`}
          onClick={() => setActiveInput("file")}
        >
          <FileUp size={17} />
          Upload file
        </button>

        <button
          type="button"
          className={`method-tab ${activeInput === "url" ? "active" : ""
            }`}
          onClick={() => setActiveInput("url")}
        >
          <Link size={17} />
          Contract URL
        </button>
      </div>

      {activeInput === "file" && (
        <section className="upload-workspace">
          {!selectedFile ? (
            <div
              className={`large-dropzone ${dragging ? "dragging" : ""
                }`}
              aria-label="Contract file upload area"
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
            >
              <div className="large-upload-icon">
                <Upload size={28} />
              </div>

              <h3>Drop your contract here</h3>

              <p>
                Drag and drop your file here, or choose one
                from your computer.
              </p>

              <button
                className="primary-button upload-select-button"
                type="button"
                onClick={() =>
                  fileInputRef.current?.click()
                }
              >
                <FileText size={17} />
                Choose a file
              </button>

              <input
                ref={fileInputRef}
                type="file"
                hidden
                accept={acceptedFileTypes.join(",")}
                onChange={handleFileChange}
              />

              <div className="supported-grid">
                <SupportedType
                  icon={FileText}
                  label="PDF"
                />

                <SupportedType
                  icon={FileText}
                  label="DOC / DOCX"
                />

                <SupportedType
                  icon={FileText}
                  label="TXT"
                />

                <SupportedType
                  icon={Image}
                  label="PNG / JPG"
                />

                <SupportedType
                  icon={Mic}
                  label="WAV / MP3 / OGG"
                />

                <SupportedType
                  icon={Video}
                  label="MP4 / MOV / AVI"
                />
              </div>

              <span className="upload-note">
                Files are processed securely by Term Shield.
              </span>
            </div>
          ) : (
            <SelectedFile
              file={selectedFile}
              onRemove={removeFile}
              uploading={uploading}
            />
          )}
        </section>
      )}

      {activeInput === "url" && (
        <section className="url-workspace">
          <div className="url-icon">
            <Link size={25} />
          </div>

          <h3>Analyze a contract webpage</h3>

          <p>
            Paste the URL of a publicly accessible contract,
            agreement, terms & conditions, policy or legal
            document.
          </p>

          <div className="url-input-wrapper">
            <Link size={18} />

            <input
              type="url"
              value={url}
              onChange={(event) => {
                setUrl(event.target.value);
                setUploadError("");
              }}
              placeholder="https://example.com/terms-and-conditions"
            />
          </div>

          <span className="url-note">
            Term Shield will retrieve the webpage and extract
            its readable contractual text.
          </span>

          <div className="url-supported-types">
            <span>Supports public</span>
            <strong>webpages, PDF, DOCX and TXT links</strong>
          </div>
        </section>
      )}

      <section className="analysis-preview">
        <div className="preview-heading">
          <div>
            <span className="card-label">AFTER UPLOAD</span>
            <h3>What Term Shield will analyze</h3>
          </div>

          <Sparkles size={19} />
        </div>

        <div className="analysis-items">
          <AnalysisItem
            title="Clauses"
            text="Identify and classify contract clauses."
          />

          <AnalysisItem
            title="Risk"
            text="Find clauses that may require attention."
          />

          <AnalysisItem
            title="Obligations"
            text="Extract responsibilities and deadlines."
          />

          <AnalysisItem
            title="Financial terms"
            text="Identify payments, fees and penalties."
          />

          <AnalysisItem
            title="AI summary"
            text="Explain the contract in plain language."
          />

          <AnalysisItem
            title="Ask My T&C"
            text="Answer questions using your contract."
          />
        </div>
      </section>

      {uploadError && (
        <div className="upload-error">
          <AlertCircle size={18} />

          <div>
            <strong>Analysis failed</strong>
            <span>{uploadError}</span>
          </div>
        </div>
      )}

      {uploadResult && (
        <div className="upload-success">
          <CheckCircle2 size={18} />

          <div>
            <strong>
              Contract uploaded successfully
            </strong>

            <span>
              File ID: {uploadResult.file_id}
            </span>

            {uploadResult.character_count !==
              undefined && (
                <span>
                  Extracted text:{" "}
                  {uploadResult.character_count.toLocaleString()}{" "}
                  characters
                </span>
              )}
          </div>
        </div>
      )}

      <div className="upload-actions">
        <button
          className="secondary-button"
          type="button"
          onClick={onBack}
          disabled={uploading}
        >
          Cancel
        </button>

        <button
          className="primary-button"
          type="button"
          disabled={!canAnalyze || uploading}
          onClick={handleAnalyze}
        >
          {uploading ? (
            <>
              <Loader2
                size={17}
                className="spin"
              />
              Processing contract...
            </>
          ) : (
            <>
              <ShieldAlert size={17} />
              Analyze contract
            </>
          )}
        </button>
      </div>
    </div>
  );
}

/* =========================
   SELECTED FILE
========================= */

function SelectedFile({ file, onRemove, uploading }) {
  const sizeInMb = (
    file.size /
    (1024 * 1024)
  ).toFixed(2);

  return (
    <div className={`selected-file-card ${uploading ? "uploading" : ""}`}>
      <div className="selected-file-icon">
        <FileText size={26} />
      </div>

      <div className="selected-file-info">
        <strong>{file.name}</strong>

        <span>
          {sizeInMb} MB · {uploading ? "Uploading securely" : "Ready for analysis"}
        </span>

        <div className={`ready-status ${uploading ? "uploading-status" : ""}`}>
          {uploading ? (
            <Loader2 size={13} className="spin" />
          ) : (
            <CheckCircle2 size={13} />
          )}
          {uploading ? "Processing contract..." : "File selected successfully"}
        </div>
      </div>

      <button
        className="remove-file-button"
        type="button"
        onClick={onRemove}
        aria-label="Remove file"
      >
        <Trash2 size={17} />
      </button>
    </div>
  );
}

/* =========================
   SUPPORTED TYPE
========================= */

function SupportedType({ icon: Icon, label }) {
  return (
    <div className="supported-type">
      <Icon size={14} />
      <span>{label}</span>
    </div>
  );
}

/* =========================
   ANALYSIS ITEM
========================= */

function AnalysisItem({ title, text }) {
  return (
    <div className="analysis-item">
      <div className="analysis-check">
        <CheckCircle2 size={15} />
      </div>

      <div>
        <strong>{title}</strong>
        <span>{text}</span>
      </div>
    </div>
  );
}

/* =========================
   STAT CARD
========================= */

function StatCard({
  label,
  value,
  detail,
  icon: Icon,
  danger,
}) {
  return (
    <div className="stat-card">
      <div
        className={`stat-icon ${danger ? "danger" : ""
          }`}
      >
        <Icon size={18} />
      </div>

      <div className="stat-content">
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
    </div>
  );
}

/* =========================
   INSIGHT
========================= */

function Insight({ title, text, icon: Icon }) {
  return (
    <div className="insight-item">
      <div className="insight-icon">
        <Icon size={17} />
      </div>

      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
    </div>
  );
}

/* =========================
   RISK ANALYSIS
========================= */

function RiskAnalysis({
  fileId,
  analysis,
}) {
  const clauses = Array.isArray(analysis)
    ? analysis
    : analysis?.analyses ||
    analysis?.clauses ||
    analysis?.results ||
    analysis?.data ||
    [];

  const highRisk = clauses.filter(
    (clause) =>
      String(
        clause?.risk_level ||
        clause?.risk ||
        clause?.riskLevel ||
        ""
      ).toLowerCase() === "high"
  );

  const mediumRisk = clauses.filter(
    (clause) =>
      String(
        clause?.risk_level ||
        clause?.risk ||
        clause?.riskLevel ||
        ""
      ).toLowerCase() === "medium"
  );

  const lowRisk = clauses.filter(
    (clause) =>
      String(
        clause?.risk_level ||
        clause?.risk ||
        clause?.riskLevel ||
        ""
      ).toLowerCase() === "low"
  );

  const riskScores = clauses
    .map(
      (clause) =>
        clause?.risk_score ??
        clause?.score ??
        clause?.riskScore
    )
    .filter((score) => Number.isFinite(Number(score)));

  const overallScore =
    analysis?.overall_risk_score ??
    analysis?.overallRiskScore ??
    (riskScores.length
      ? Math.round(
        riskScores.reduce(
          (total, score) => total + Number(score),
          0
        ) / riskScores.length
      )
      : 0);

  const overallRisk =
    analysis?.overall_risk ||
    analysis?.overallRisk ||
    (highRisk.length
      ? "HIGH"
      : mediumRisk.length
        ? "MEDIUM"
        : lowRisk.length
          ? "LOW"
          : "UNRATED");

  const overallRiskDescription =
    overallRisk.toLowerCase() === "high"
      ? "Priority review recommended before you rely on this agreement."
      : overallRisk.toLowerCase() === "medium"
        ? "A focused review can clarify the clauses most likely to affect you."
        : overallRisk.toLowerCase() === "low"
          ? "No major risk signals were detected in the analyzed clauses."
          : "Analyze a contract to establish its risk profile.";

  return (
    <div className="analysis-page">
      <section className="analysis-page-header">
        <div>
          <span className="eyebrow">
            AI CONTRACT ANALYSIS
          </span>

          <h2>Risk Analysis</h2>

          <p>
            Term Shield has analyzed the clauses in your
            contract and identified areas that may require
            attention.
          </p>
        </div>

        <div className="analysis-file-id">
          <span>CONTRACT ID</span>

          <strong>
            {fileId || "Unavailable"}
          </strong>
        </div>
      </section>

      <section className="risk-summary-hero">
        <div className="risk-summary-copy">
          <div className="section-kicker">
            <ShieldAlert size={14} />
            EXECUTIVE RISK SUMMARY
          </div>

          <h3>
            {overallRisk.toLowerCase() === "unrated"
              ? "No risk profile yet"
              : `${overallRisk} risk profile`}
          </h3>

          <p>{overallRiskDescription}</p>
        </div>

        <div className={`overall-score ${overallRisk.toLowerCase()}`}>
          <span>OVERALL RISK SCORE</span>
          <strong>{overallScore}</strong>
          <small>out of 100</small>
        </div>
      </section>

      <section className="risk-overview-grid">
        <div className="risk-stat-card">
          <div className="risk-stat-icon neutral">
            <FileText size={16} />
          </div>
          <span>Total clauses</span>
          <strong>{clauses.length}</strong>
          <small>Detected in contract</small>
        </div>

        <div className="risk-stat-card high">
          <div className="risk-stat-icon high">
            <AlertCircle size={16} />
          </div>
          <span>High risk</span>
          <strong>{highRisk.length}</strong>
          <small>Requires attention</small>
        </div>

        <div className="risk-stat-card medium">
          <div className="risk-stat-icon medium">
            <ShieldAlert size={16} />
          </div>
          <span>Medium risk</span>
          <strong>{mediumRisk.length}</strong>
          <small>Review recommended</small>
        </div>

        <div className="risk-stat-card low">
          <div className="risk-stat-icon low">
            <CheckCircle2 size={16} />
          </div>
          <span>Low risk</span>
          <strong>{lowRisk.length}</strong>
          <small>Lower concern</small>
        </div>
      </section>

      <section className="dashboard-card">
        <div className="card-heading">
          <div>
            <span className="card-label">
              CLAUSE INTELLIGENCE
            </span>

            <h3>Detected contract clauses</h3>
          </div>

          <ShieldAlert size={20} />
        </div>

        {!fileId ? (
          <div className="empty-state">
            <div className="empty-icon">
              <FileText size={23} />
            </div>

            <h4>No contract selected</h4>

            <p>
              Select an analyzed contract from your library or upload a new agreement to review its risk analysis and clause scoring.
            </p>
          </div>
        ) : clauses.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <AlertCircle size={23} />
            </div>

            <h4>No clause records returned</h4>

            <p>
              The backend responded successfully, but the
              analysis response did not contain a recognizable
              clause list. Check the browser console for the
              raw response.
            </p>
          </div>
        ) : (
          <div className="clause-analysis-list">
            {clauses.map((clause, index) => {
              const risk =
                clause?.risk_level ||
                clause?.risk ||
                clause?.riskLevel ||
                "Unknown";

              const title =
                clause?.title ||
                clause?.clause_title ||
                clause?.clause_type ||
                clause?.classification ||
                `Clause ${index + 1}`;

              const meaning =
                clause?.meaning ||
                clause?.plain_language ||
                clause?.explanation ||
                clause?.summary ||
                clause?.text ||
                "No explanation available.";

              const score =
                clause?.risk_score ??
                clause?.score ??
                clause?.riskScore;

              const normalizedRisk =
                String(risk).toLowerCase();

              const reasons = Array.isArray(clause?.risk_reasons)
                ? clause.risk_reasons
                : clause?.risk_reasons
                  ? [clause.risk_reasons]
                  : [];

              const recommendations = Array.isArray(
                clause?.recommendations
              )
                ? clause.recommendations
                : clause?.recommendations
                  ? [clause.recommendations]
                  : [];

              return (
                <div
                  className={`clause-analysis-card ${normalizedRisk}`}
                  key={
                    clause?.clause_id ||
                    clause?.id ||
                    index
                  }
                >
                  <div className="clause-analysis-top">
                    <div>
                      <span className="clause-number">
                        CLAUSE {index + 1}
                      </span>

                      <h4>{title}</h4>
                    </div>

                    <span
                      className={`risk-badge ${normalizedRisk}`}
                    >
                      <span className="risk-badge-dot" />
                      {risk}
                    </span>
                  </div>

                  <p>{meaning}</p>

                  {(reasons.length > 0 || clause?.user_impact) && (
                    <div className="clause-detail-block">
                      <span className="clause-detail-label">
                        <AlertCircle size={13} />
                        Why this matters
                      </span>

                      <ul>
                        {reasons.map((reason, reasonIndex) => (
                          <li key={reasonIndex}>{reason}</li>
                        ))}
                        {clause?.user_impact && (
                          <li>{clause.user_impact}</li>
                        )}
                      </ul>
                    </div>
                  )}

                  {recommendations.length > 0 && (
                    <div className="clause-detail-block recommendation-block">
                      <span className="clause-detail-label">
                        <CheckCircle2 size={13} />
                        Recommended next step
                      </span>

                      <ul>
                        {recommendations.map((recommendation, recommendationIndex) => (
                          <li key={recommendationIndex}>{recommendation}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {score !== undefined && (
                    <div className="risk-score">
                      <span>Risk score</span>
                      <strong>{score}</strong>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {Boolean(analysis) && (
        <details className="debug-analysis">
          <summary>
            View raw AI analysis response
          </summary>

          <pre>
            {JSON.stringify(
              analysis,
              null,
              2
            )}
          </pre>
        </details>
      )}
    </div>
  );
}

function AnalysisLoadingState() {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Loader2 size={23} className="spin" />
      </div>
      <h4>Loading contract analysis...</h4>
      <p>Term Shield is retrieving the selected contract insights.</p>
    </div>
  );
}

function AnalysisErrorState({ message, onBack }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <AlertCircle size={23} />
      </div>
      <h4>Unable to load contract analysis</h4>
      <p>{message}</p>
      <button
        className="secondary-button"
        type="button"
        onClick={onBack}
      >
        Back to contracts
      </button>
    </div>
  );
}

/* =========================
   CONTRACTS
========================= */

function ContractsPage({
  fileId,
  analysis,
  contracts: persistedContracts,
  contractsLoading,
  contractsError,
  onSelectContract,
  onDeleteContract,
  onNavigate,
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const [contractToDelete, setContractToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const handleOpenDelete = (e, contract) => {
    e.stopPropagation();
    setContractToDelete(contract);
    setDeleteError("");
  };

  const handleCloseDelete = () => {
    if (isDeleting) return;
    setContractToDelete(null);
    setDeleteError("");
  };

  const handleConfirmDelete = async () => {
    if (!contractToDelete || isDeleting) return;
    setIsDeleting(true);
    setDeleteError("");
    try {
      if (onDeleteContract) {
        await onDeleteContract(contractToDelete.id);
      }
      setContractToDelete(null);
    } catch (err) {
      setDeleteError(
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "Unable to delete contract. Please try again."
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const contracts = persistedContracts.map((contract) => ({
    id: contract.id,
    name: contract.filename,
    type: String(contract.file_type || "document").toUpperCase(),
    date: contract.created_at
      ? new Date(contract.created_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
      : "Unknown date",
    status: contract.status || "Unknown",
    risk: String(contract.overall_risk || "unrated").toLowerCase(),
  }));

  const visibleContracts = contracts.filter((contract) => {
    const matchesSearch = contract.name
      .toLowerCase()
      .includes(searchTerm.trim().toLowerCase());
    const matchesRisk =
      riskFilter === "all" || contract.risk === riskFilter;
    const matchesStatus =
      statusFilter === "all" ||
      contract.status.toLowerCase() === statusFilter;

    return matchesSearch && matchesRisk && matchesStatus;
  });

  if (contractsLoading || contractsError) {
    return (
      <div className="contracts-page">
        <section className="contracts-page-header">
          <div>
            <span className="eyebrow">CONTRACT LIBRARY</span>
            <h2>Your contracts, in one clear view.</h2>
            <p>
              Keep every analyzed agreement close at hand and move
              from document to decision without losing context.
            </p>
          </div>

          <button
            className="primary-button"
            type="button"
            onClick={() => onNavigate("upload")}
          >
            <Upload size={17} />
            Upload contract
          </button>
        </section>

        <section className="contracts-empty-state">
          {contractsError ? (
            <>
              <h3>Unable to load contracts</h3>
              <p>{contractsError}</p>
            </>
          ) : (
            <h3>Loading your contract library...</h3>
          )}
        </section>
      </div>
    );
  }

  return (
    <div className="contracts-page">
      <section className="contracts-page-header">
        <div>
          <span className="eyebrow">CONTRACT LIBRARY</span>
          <h2>Your contracts, in one clear view.</h2>
          <p>
            Keep every analyzed agreement close at hand and move
            from document to decision without losing context.
          </p>
        </div>

        <button
          className="primary-button"
          type="button"
          onClick={() => onNavigate("upload")}
        >
          <Upload size={17} />
          Upload contract
        </button>
      </section>

      <section className="contracts-toolbar" aria-label="Contract filters">
        <div className="contracts-search">
          <Search size={17} />
          <input
            type="search"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search by contract name..."
            aria-label="Search contracts"
          />
        </div>

        <div className="contract-filter-group">
          <label>
            Risk
            <select
              value={riskFilter}
              onChange={(event) => setRiskFilter(event.target.value)}
            >
              <option value="all">All risk levels</option>
              <option value="high">High risk</option>
              <option value="medium">Medium risk</option>
              <option value="low">Low risk</option>
              <option value="unrated">Unrated</option>
            </select>
          </label>

          <label>
            Status
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="all">All statuses</option>
              <option value="analyzed">Analyzed</option>
            </select>
          </label>
        </div>
      </section>

      <div className="contracts-list-heading">
        <div>
          <span className="card-label">YOUR LIBRARY</span>
          <h3>{visibleContracts.length} contract{visibleContracts.length === 1 ? "" : "s"}</h3>
        </div>
        <span>{contracts.length ? "Sorted by latest activity" : "No documents yet"}</span>
      </div>

      {visibleContracts.length ? (
        <section className="contracts-list" aria-label="Contracts">
          {visibleContracts.map((contract) => (
            <div
              className="contract-library-card"
              key={contract.id}
              onClick={() => onSelectContract(contract.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  onSelectContract(contract.id);
                }
              }}
            >
              <div className="contract-library-icon">
                <FileText size={22} />
              </div>

              <div className="contract-library-main">
                <div className="contract-library-title-row">
                  <strong>{contract.name}</strong>
                  <span className={`library-risk-badge ${contract.risk}`}>
                    {contract.risk === "unrated" ? "Unrated" : `${contract.risk} risk`}
                  </span>
                </div>
                <span className="contract-library-id">ID {contract.id}</span>
              </div>

              <div className="contract-library-meta">
                <span>{contract.type}</span>
                <span>{contract.date}</span>
              </div>

              <div className="contract-library-status">
                <CheckCircle2 size={15} />
                {contract.status}
              </div>

              <div className="contract-card-actions">
                <button
                  type="button"
                  className="contract-delete-btn"
                  title={`Delete ${contract.name}`}
                  aria-label={`Delete ${contract.name}`}
                  onClick={(e) => handleOpenDelete(e, contract)}
                >
                  <Trash2 size={16} />
                </button>
                <ChevronDown className="contract-library-arrow" size={18} />
              </div>
            </div>
          ))}
        </section>
      ) : (
        <section className="contracts-empty-state">
          <div className="contracts-empty-icon">
            <FileText size={25} />
          </div>
          <span className="card-label">NO MATCHES YET</span>
          <h3>{contracts.length ? "No contracts match those filters." : "Your contract library is ready."}</h3>
          <p>
            {contracts.length
              ? "Try a different search term or reset the filters."
              : "Upload your first agreement to start building a focused, searchable library."}
          </p>
          <button
            className="secondary-button"
            type="button"
            onClick={() => onNavigate("upload")}
          >
            <Upload size={15} />
            Upload contract
          </button>
        </section>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {contractToDelete && (
        <div className="delete-modal-backdrop" onClick={handleCloseDelete}>
          <div
            className="delete-modal-dialog"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-dialog-title"
          >
            <div className="delete-modal-header">
              <div className="delete-modal-icon">
                <Trash2 size={22} />
              </div>
              <div>
                <span className="card-label">CONFIRM DELETION</span>
                <h3 id="delete-dialog-title">Delete Contract</h3>
              </div>
            </div>

            <div className="delete-modal-body">
              <p>
                Are you sure you want to delete <strong>{contractToDelete.name}</strong>?
              </p>
              <p className="delete-warning-text">
                This will permanently remove this contract along with its extracted clauses,
                risk assessments, and Q&amp;A history from your workspace.
                This action cannot be undone.
              </p>

              {deleteError && (
                <div className="delete-error-alert" role="alert">
                  <AlertCircle size={16} />
                  <span>{deleteError}</span>
                </div>
              )}
            </div>

            <div className="delete-modal-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={handleCloseDelete}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="danger-button delete-confirm-btn"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? (
                  <>
                    <Loader2 size={15} className="spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 size={15} />
                    <span>Delete Contract</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* =========================
   SETTINGS PAGE
========================= */

function SettingsPage({
  currentUser,
  userLoading,
  onLogout,
  onRefreshUser,
  userDisplayName,
  userPhoto,
  userInitials,
  onEditProfile,
}) {
  const [preferences, setPreferences] = useState(() => {
    try {
      const saved = localStorage.getItem("termShieldPreferences");
      if (saved) return JSON.parse(saved);
    } catch {
      // ignore
    }
    return {
      riskSensitivity: "balanced",
      autoAnalyze: true,
      clauseView: "detailed",
      dateFormat: "locale",
    };
  });

  const [savedStatus, setSavedStatus] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const handlePreferenceChange = (key, value) => {
    const updated = { ...preferences, [key]: value };
    setPreferences(updated);
    try {
      localStorage.setItem("termShieldPreferences", JSON.stringify(updated));
      setSavedStatus(true);
      setTimeout(() => setSavedStatus(false), 2200);
    } catch {
      // ignore
    }
  };

  const handleResetPreferences = () => {
    const defaults = {
      riskSensitivity: "balanced",
      autoAnalyze: true,
      clauseView: "detailed",
      dateFormat: "locale",
    };
    setPreferences(defaults);
    try {
      localStorage.setItem("termShieldPreferences", JSON.stringify(defaults));
      setSavedStatus(true);
      setTimeout(() => setSavedStatus(false), 2200);
    } catch {
      // ignore
    }
  };

  const handleManualRefresh = async () => {
    if (onRefreshUser) {
      setRefreshing(true);
      try {
        await onRefreshUser();
      } finally {
        setRefreshing(false);
      }
    }
  };

  const initials = userInitials || (currentUser?.full_name
    ? currentUser.full_name
      .trim()
      .split(/\s+/)
      .map((p) => p[0]?.toUpperCase())
      .slice(0, 2)
      .join("") || "TS"
    : currentUser?.email
      ? currentUser.email.slice(0, 2).toUpperCase()
      : "TS");

  const memberSince = currentUser?.created_at
    ? new Date(currentUser.created_at).toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    })
    : "Active session";

  return (
    <div className="settings-page">
      <section className="settings-page-header">
        <div>
          <span className="eyebrow">SETTINGS &amp; PREFERENCES</span>
          <h2>Workspace &amp; Account</h2>
          <p>
            Review your authenticated user profile, security parameters, and client workspace preferences.
          </p>
        </div>

        <div className="settings-header-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={handleManualRefresh}
            disabled={refreshing || userLoading}
            title="Refresh profile from server"
          >
            <RefreshCw size={15} className={refreshing || userLoading ? "spin" : ""} />
            <span>{refreshing ? "Refreshing..." : "Refresh Session"}</span>
          </button>

          <button
            type="button"
            className="settings-logout-button"
            onClick={onLogout}
            title="End your active session"
          >
            <LogOut size={15} />
            <span>Log out</span>
          </button>
        </div>
      </section>

      {userLoading && !currentUser ? (
        <section className="settings-loading-card">
          <Loader2 size={24} className="spin" />
          <p>Loading authenticated account profile...</p>
        </section>
      ) : !currentUser ? (
        <section className="settings-empty-card">
          <AlertCircle size={28} />
          <h3>Session information unavailable</h3>
          <p>Unable to retrieve user credentials. Please re-authenticate.</p>
          <button type="button" className="primary-button" onClick={onLogout}>
            Return to Login
          </button>
        </section>
      ) : (
        <div className="settings-grid">
          {/* Profile Overview Card */}
          <section className="settings-card settings-profile-card">
            <div className="settings-card-header">
              <div className="settings-card-icon">
                <Users size={18} />
              </div>
              <div>
                <span className="card-label">AUTHENTICATED IDENTITY</span>
                <h3>User Profile</h3>
              </div>
            </div>

            <div className="settings-profile-badge-row">
              <div className="settings-large-avatar">
                {userPhoto ? (
                  <img src={userPhoto} alt={userDisplayName || "Profile"} className="settings-avatar-img" />
                ) : (
                  initials
                )}
              </div>
              <div className="settings-profile-main">
                <div className="settings-profile-title-row">
                  <h4>{userDisplayName || currentUser.full_name || "Term Shield User"}</h4>
                  {onEditProfile && (
                    <button
                      type="button"
                      className="secondary-button edit-profile-badge-btn"
                      onClick={onEditProfile}
                      title="Edit Profile"
                    >
                      <User size={13} />
                      <span>Edit Profile</span>
                    </button>
                  )}
                </div>
                <p>{currentUser.email}</p>
                <div className="settings-tags">
                  <span className={`settings-status-pill ${currentUser.is_active ? "active" : "inactive"}`}>
                    <span className="status-dot" />
                    {currentUser.is_active ? "Account Active" : "Account Inactive"}
                  </span>
                  <span className={`settings-status-pill ${currentUser.is_verified ? "verified" : "unverified"}`}>
                    <CheckCircle2 size={12} />
                    {currentUser.is_verified ? "Email Verified" : "Verification Pending"}
                  </span>
                </div>
              </div>
            </div>

            <div className="settings-fields-grid">
              <div className="settings-field-item">
                <span className="field-label">FULL NAME</span>
                <span className="field-value">{userDisplayName || currentUser.full_name || "Not specified"}</span>
              </div>

              <div className="settings-field-item">
                <span className="field-label">EMAIL ADDRESS</span>
                <span className="field-value">{currentUser.email}</span>
              </div>

              <div className="settings-field-item">
                <span className="field-label">ACCOUNT ID</span>
                <span className="field-value mono-id">{currentUser.id}</span>
              </div>

              <div className="settings-field-item">
                <span className="field-label">MEMBER SINCE</span>
                <span className="field-value">{memberSince}</span>
              </div>
            </div>

            <div className="settings-notice-box">
              <Sparkles size={14} />
              <span>
                Account profile data is synchronized with your active authentication session. To modify your legal name or primary email, please contact your workspace administrator.
              </span>
            </div>
          </section>

          {/* Security & Authentication Card */}
          <section className="settings-card settings-security-card">
            <div className="settings-card-header">
              <div className="settings-card-icon security">
                <ShieldCheck size={18} />
              </div>
              <div>
                <span className="card-label">DATA &amp; ACCESS SECURITY</span>
                <h3>Authentication &amp; Security</h3>
              </div>
            </div>

            <div className="settings-security-list">
              <div className="security-item">
                <div className="security-item-icon">
                  <KeyRound size={16} />
                </div>
                <div className="security-item-content">
                  <strong>Password Protection</strong>
                  <p>Encrypted using strong cryptographic hashing (Argon2id/bcrypt). Plaintext passwords are never stored or transmitted in the clear.</p>
                </div>
                <span className="security-item-status verified">Secured</span>
              </div>

              <div className="security-item">
                <div className="security-item-icon">
                  <CheckCircle2 size={16} />
                </div>
                <div className="security-item-content">
                  <strong>Token Authentication</strong>
                  <p>Protected by JSON Web Tokens (JWT) using HMAC-SHA256 signature verification with 60-minute automatic expiration.</p>
                </div>
                <span className="security-item-status verified">Active</span>
              </div>

              <div className="security-item">
                <div className="security-item-icon">
                  <Users size={16} />
                </div>
                <div className="security-item-content">
                  <strong>Contract Ownership Isolation</strong>
                  <p>Every uploaded document and extracted clause is strictly bound to your user ID. Cross-tenant access is blocked at the database and API layer.</p>
                </div>
                <span className="security-item-status verified">Enforced</span>
              </div>
            </div>

            <div className="security-actions-row">
              <span className="security-footnote">
                Need to reset credentials or revoke session? Log out below to invalidate current browser tokens.
              </span>
              <button
                type="button"
                className="secondary-button"
                onClick={onLogout}
              >
                <LogOut size={14} />
                <span>Log out</span>
              </button>
            </div>
          </section>

          {/* Workspace Preferences Card */}
          <section className="settings-card settings-preferences-card">
            <div className="settings-card-header">
              <div className="settings-card-icon preferences">
                <Sliders size={18} />
              </div>
              <div>
                <span className="card-label">LOCAL CLIENT CONFIGURATION</span>
                <h3>Workspace Preferences</h3>
              </div>

              {savedStatus && (
                <span className="preferences-saved-indicator">
                  <CheckCircle2 size={13} />
                  Saved locally
                </span>
              )}
            </div>

            <p className="preferences-description">
              These settings control how contracts and analyses are presented in your browser session. Preferences are saved automatically to your device&apos;s local storage.
            </p>

            <div className="preferences-grid">
              <div className="preference-group">
                <label htmlFor="pref-risk-sensitivity">
                  <span className="pref-title-with-icon">
                    Default Risk Sensitivity
                    <Info size={13} className="setting-info-icon" />
                  </span>
                  <span className="pref-hint">Controls how sensitive Term Shield is when identifying potential contract risks.</span>
                </label>
                <select
                  id="pref-risk-sensitivity"
                  value={preferences.riskSensitivity}
                  onChange={(e) => handlePreferenceChange("riskSensitivity", e.target.value)}
                >
                  <option value="balanced">Balanced (Standard AI detection)</option>
                  <option value="conservative">Strict (Elevate warnings on ambiguous clauses)</option>
                  <option value="relaxed">Relaxed (Focus only on critical obligations)</option>
                </select>
              </div>

              <div className="preference-group">
                <label htmlFor="pref-clause-view">
                  <span className="pref-title-with-icon">
                    Clause Explorer Default Layout
                    <Info size={13} className="setting-info-icon" />
                  </span>
                  <span className="pref-hint">Controls how clause information is displayed when Clause Explorer opens.</span>
                </label>
                <select
                  id="pref-clause-view"
                  value={preferences.clauseView}
                  onChange={(e) => handlePreferenceChange("clauseView", e.target.value)}
                >
                  <option value="detailed">Detailed (Full text, risk badge, and entity tags)</option>
                  <option value="compact">Compact (High-density list view)</option>
                </select>
              </div>

              <div className="preference-group">
                <label htmlFor="pref-date-format">
                  <span className="pref-title-with-icon">
                    Date &amp; Timestamp Display
                    <Info size={13} className="setting-info-icon" />
                  </span>
                  <span className="pref-hint">Controls how contract and analysis dates are displayed throughout the workspace.</span>
                </label>
                <select
                  id="pref-date-format"
                  value={preferences.dateFormat}
                  onChange={(e) => handlePreferenceChange("dateFormat", e.target.value)}
                >
                  <option value="locale">Locale Standard (e.g. Sep 17, 2026)</option>
                  <option value="iso">ISO 8601 (YYYY-MM-DD)</option>
                </select>
              </div>

              <div className="preference-toggle-group">
                <div className="toggle-label-wrap">
                  <span className="pref-title-with-icon">
                    <strong>Auto-analyze upon upload</strong>
                    <Info size={13} className="setting-info-icon" />
                  </span>
                  <span>Automatically analyze newly uploaded contracts for clauses and risk signals.</span>
                </div>
                <label className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={preferences.autoAnalyze}
                    onChange={(e) => handlePreferenceChange("autoAnalyze", e.target.checked)}
                  />
                  <span className="toggle-slider" />
                </label>
              </div>
            </div>

            <div className="preferences-footer">
              <button
                type="button"
                className="secondary-button text-button"
                onClick={handleResetPreferences}
              >
                Reset to Defaults
              </button>
              <span className="preferences-storage-note">Stored in browser localStorage • Not sent to backend</span>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

/* ==============================================
   EDIT PROFILE MODAL
============================================== */

function EditProfileModal({
  initialName,
  initialPhoto,
  userInitials,
  userEmail,
  onClose,
  onSave,
}) {
  const [name, setName] = useState(initialName || "");
  const [photo, setPhoto] = useState(initialPhoto || null);
  const fileInputRef = useRef(null);

  const handlePhotoSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      alert("Please select an image file (JPG, PNG, WebP).");
      return;
    }
    if (file.size > 3 * 1024 * 1024) {
      alert("Image size should be under 3MB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      setPhoto(event.target?.result);
    };
    reader.readAsDataURL(file);
  };

  const handleRemovePhoto = () => {
    setPhoto(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(name, photo);
  };

  return (
    <div className="ts-modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="ts-modal-dialog edit-profile-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="ts-modal-header">
          <div>
            <span className="eyebrow">USER PROFILE</span>
            <h3>Edit Profile</h3>
            <p>Update your display name and personal avatar</p>
          </div>
          <button type="button" className="ts-modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="edit-profile-form">
          {/* Photo Section */}
          <div className="edit-profile-avatar-row">
            <div className="edit-avatar-container">
              {photo ? (
                <img src={photo} alt="Profile" className="edit-avatar-img" />
              ) : (
                <div className="edit-avatar-initials">{userInitials}</div>
              )}
            </div>

            <div className="edit-avatar-controls">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png, image/jpeg, image/webp"
                onChange={handlePhotoSelect}
                style={{ display: "none" }}
              />
              <div className="edit-avatar-btn-group">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Camera size={14} />
                  <span>{photo ? "Change Photo" : "Upload Photo"}</span>
                </button>
                {photo && (
                  <button
                    type="button"
                    className="secondary-button text-danger"
                    onClick={handleRemovePhoto}
                  >
                    <Trash2 size={14} />
                    <span>Remove</span>
                  </button>
                )}
              </div>
              <span className="edit-avatar-hint">
                Recommended 1:1 square. Stored locally in your browser.
              </span>
            </div>
          </div>

          {/* Name Field */}
          <div className="edit-profile-field">
            <label htmlFor="edit-profile-name">
              Full Name / Display Name
            </label>
            <input
              id="edit-profile-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Jane Doe"
              required
            />
          </div>

          {/* Email Field (Read-only) */}
          <div className="edit-profile-field">
            <label htmlFor="edit-profile-email">
              Email Address <span className="read-only-tag">(Read-only)</span>
            </label>
            <input
              id="edit-profile-email"
              type="email"
              value={userEmail || ""}
              readOnly
              disabled
              className="disabled-input"
            />
            <span className="field-hint">
              Authentication email is managed by your sign-in provider and cannot be changed here.
            </span>
          </div>

          {/* Modal Footer */}
          <div className="ts-modal-footer">
            <button
              type="button"
              className="secondary-button"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="primary-button"
            >
              <CheckCircle2 size={16} />
              <span>Save Changes</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ==============================================
   HELP & SUPPORT MODAL
============================================== */

function HelpSupportModal({ onClose }) {
  const [openFaqIndex, setOpenFaqIndex] = useState(null);

  const toggleFaq = (index) => {
    setOpenFaqIndex((prev) => (prev === index ? null : index));
  };

  const faqs = [
    {
      q: "How do I upload a contract?",
      a: "Navigate to 'Upload Contract' in the sidebar or click 'Upload contract' on the dashboard. Drag and drop any supported file (PDF, TXT, image, audio, video) or enter a live webpage URL, then click Analyze.",
    },
    {
      q: "Where can I see my previous contracts?",
      a: "All ingested contracts are stored in your workspace library. You can view, search, and inspect them from the 'Contracts' section in the sidebar or under the Recent Contracts table on your Dashboard.",
    },
    {
      q: "How does Ask My T&C work?",
      a: "Select a contract and click 'Ask My T&C' in the header or sidebar. Type questions regarding obligations, cancellation charges, deadlines, or risks. The AI assistant answers using strictly verified clauses and can explain terms in regional languages like Telugu, Hindi, Spanish, and English.",
    },
    {
      q: "Can Term Shield answer questions unrelated to my contract?",
      a: "Term Shield prioritizes contract evidence grounding. If a topic is not present in the contract text, the assistant explicitly states that rather than fabricating information.",
    },
    {
      q: "Can I change my profile information?",
      a: "Yes. Click your profile avatar at the bottom of the sidebar, select 'Edit Profile', and you can update your display name or upload a custom profile avatar photo.",
    },
    {
      q: "How do I reset my workspace preferences?",
      a: "Navigate to Settings from the sidebar or profile dropdown, scroll to 'Workspace Preferences', and click 'Reset to Defaults'. This restores sensitivity without modifying your profile, photo, or login session.",
    },
  ];

  return (
    <div className="ts-modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="ts-modal-dialog help-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="ts-modal-header">
          <div>
            <span className="eyebrow">HELP &amp; DOCUMENTATION</span>
            <h3>Help &amp; Support Center</h3>
            <p>Explore Term Shield workflows, supported inputs, risk analysis, and common FAQs.</p>
          </div>
          <button type="button" className="ts-modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <div className="ts-modal-body">
          {/* A. HOW TERM SHIELD WORKS */}
          <section className="help-section">
            <h4 className="help-section-title">A. How Term Shield Works</h4>
            <p className="help-section-desc">
              Term Shield converts complex, lengthy legal agreements into actionable intelligence through an automated 6-step pipeline:
            </p>
            <div className="help-workflow-grid">
              <div className="help-step-card">
                <span className="help-step-number">1</span>
                <strong>Upload Contract</strong>
                <p>Ingest document files, audio, video recordings, or webpage URLs.</p>
              </div>
              <div className="help-step-card">
                <span className="help-step-number">2</span>
                <strong>Extract Content</strong>
                <p>Extract text using multimodal OCR, transcription, and HTML parsing.</p>
              </div>
              <div className="help-step-card">
                <span className="help-step-number">3</span>
                <strong>Identify Clauses</strong>
                <p>Segment text into clauses, categories, and legal classifications.</p>
              </div>
              <div className="help-step-card">
                <span className="help-step-number">4</span>
                <strong>Analyze Risks</strong>
                <p>Classify risk severity (High, Medium, Low) and calculate a 0–100 risk score.</p>
              </div>
              <div className="help-step-card">
                <span className="help-step-number">5</span>
                <strong>Generate Summary</strong>
                <p>Produce executive takeaways, customer obligations, and dependency maps.</p>
              </div>
              <div className="help-step-card">
                <span className="help-step-number">6</span>
                <strong>Ask My T&amp;C</strong>
                <p>Ask natural questions grounded strictly in contract clauses.</p>
              </div>
            </div>
          </section>

          {/* B. SUPPORTED INPUTS */}
          <section className="help-section">
            <h4 className="help-section-title">B. Supported Inputs</h4>
            <div className="help-inputs-grid">
              <div className="help-input-card">
                <div className="input-card-header">
                  <FileText size={18} />
                  <strong>Text &amp; Documents</strong>
                </div>
                <span className="input-format-badge">.pdf, .txt, .doc, .docx</span>
                <p>Native or scanned contracts, vendor agreements, and leases.</p>
              </div>

              <div className="help-input-card">
                <div className="input-card-header">
                  <Image size={18} />
                  <strong>Image Scans</strong>
                </div>
                <span className="input-format-badge">.png, .jpg, .jpeg</span>
                <p>High-resolution contract photographs and document page scans via OCR.</p>
              </div>

              <div className="help-input-card">
                <div className="input-card-header">
                  <Mic size={18} />
                  <strong>Audio Agreements</strong>
                </div>
                <span className="input-format-badge">.wav, .mp3, .ogg</span>
                <p>Voice dictations, oral contract discussions, and recorded consent.</p>
              </div>

              <div className="help-input-card">
                <div className="input-card-header">
                  <Video size={18} />
                  <strong>Video Recordings</strong>
                </div>
                <span className="input-format-badge">.mp4, .mov, .avi</span>
                <p>Video presentations, legal consent walkthroughs, and conference terms.</p>
              </div>

              <div className="help-input-card">
                <div className="input-card-header">
                  <Link size={18} />
                  <strong>Webpages &amp; URLs</strong>
                </div>
                <span className="input-format-badge">HTTP / HTTPS</span>
                <p>Live Terms of Service, Privacy Policies, and online SaaS agreements.</p>
              </div>
            </div>
          </section>

          {/* C. ASK MY T&C */}
          <section className="help-section">
            <h4 className="help-section-title">C. Ask My T&amp;C</h4>
            <div className="help-callout-card">
              <div className="help-callout-icon">
                <MessageSquare size={20} />
              </div>
              <div className="help-callout-content">
                <strong>Grounded Conversational Intelligence</strong>
                <p>
                  Ask My T&amp;C enables you to ask direct questions about the currently active contract. You can inquire about:
                </p>
                <ul className="help-list">
                  <li><strong>Customer obligations</strong> — duties, required notices, and deadlines</li>
                  <li><strong>Payment terms</strong> — recurring charges, billing cycles, late fees</li>
                  <li><strong>Cancellation &amp; termination</strong> — penalty fees, early exit clauses, and refund policies</li>
                  <li><strong>Liabilities &amp; indemnification</strong> — damages caps and legal remedies</li>
                  <li><strong>Multilingual explanations</strong> — translate and explain terms in Telugu, Hindi, Spanish, or English</li>
                </ul>
              </div>
            </div>
          </section>

          {/* D. RISK ANALYSIS */}
          <section className="help-section">
            <h4 className="help-section-title">D. Risk Analysis</h4>
            <p className="help-section-desc">
              Term Shield evaluates contract clauses against standard compliance risks, unilateral rights, and hidden financial obligations:
            </p>
            <div className="help-risk-breakdown">
              <div className="help-risk-tier high">
                <span className="risk-tier-badge">HIGH RISK</span>
                <p>Clauses that impose severe liabilities, automatic forfeiture, broad indemnities, or unilateral termination rights.</p>
              </div>
              <div className="help-risk-tier medium">
                <span className="risk-tier-badge">MEDIUM RISK</span>
                <p>Clauses with ambiguous definitions, short notice periods, auto-renewals, or conditional restrictions.</p>
              </div>
              <div className="help-risk-tier low">
                <span className="risk-tier-badge">LOW RISK</span>
                <p>Standard mutual protections, confidentiality covenants, governing law, and boilerplate definitions.</p>
              </div>
            </div>
          </section>

          {/* E. CLAUSE EXPLORER */}
          <section className="help-section">
            <h4 className="help-section-title">E. Clause Explorer</h4>
            <p className="help-section-desc">
              Inspect every segmented clause individually. Use category filters (Payment, Confidentiality, Termination, Liability) or search keywords. Switch between Detailed view for clause text and entity tags, or Compact view for rapid browsing.
            </p>
          </section>

          {/* F. REPORTS */}
          <section className="help-section">
            <h4 className="help-section-title">F. Reports</h4>
            <p className="help-section-desc">
              Access consolidated contract summaries, risk distribution charts, and executive audit overviews ready for presentation or compliance documentation.
            </p>
          </section>

          {/* G. COMMON QUESTIONS / FAQ */}
          <section className="help-section">
            <h4 className="help-section-title">G. Common Questions / FAQ</h4>
            <div className="faq-list">
              {faqs.map((faq, index) => {
                const isOpen = openFaqIndex === index;
                return (
                  <div key={index} className={`faq-item ${isOpen ? "open" : ""}`}>
                    <button
                      type="button"
                      className="faq-question-btn"
                      onClick={() => toggleFaq(index)}
                      aria-expanded={isOpen}
                    >
                      <span>{faq.q}</span>
                      <ChevronRight size={16} className={`faq-arrow ${isOpen ? "rotated" : ""}`} />
                    </button>
                    {isOpen && (
                      <div className="faq-answer-panel">
                        <p>{faq.a}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* H. NEED MORE HELP */}
          <section className="help-section">
            <h4 className="help-section-title">H. Need More Help?</h4>
            <div className="help-support-box">
              <Sparkles size={16} />
              <span>Support contact will be available here in the production release.</span>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

/* ==============================================
   ABOUT TERM SHIELD MODAL
============================================== */

function AboutTermShieldModal({ onClose }) {
  const capabilities = [
    "Multi-format contract ingestion",
    "Clause extraction",
    "Risk analysis",
    "Contract summaries",
    "Clause relationships",
    "Ask My T&C",
    "Evidence-grounded answers",
  ];

  return (
    <div className="ts-modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="ts-modal-dialog about-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="ts-modal-header borderless">
          <button type="button" className="ts-modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <div className="about-modal-content">
          {/* Brand Header */}
          <div className="about-brand-header">
            <div className="about-brand-mark">
              <ShieldAlert size={32} />
            </div>
            <h2>Term Shield</h2>
            <p className="about-tagline">Contract Intelligence</p>
            <span className="about-version-badge">Version 0.1.0</span>
          </div>

          {/* Description */}
          <p className="about-description">
            Term Shield is an AI-powered contract intelligence platform that helps users understand contracts, identify important clauses, analyze potential risks, and ask questions about contract content.
          </p>

          {/* What Term Shield Does */}
          <div className="about-features-card">
            <h4>What Term Shield Does</h4>
            <ul className="about-features-list">
              {capabilities.map((cap, idx) => (
                <li key={idx} className="about-feature-item">
                  <CheckCircle2 size={16} className="feature-check-icon" />
                  <span>{cap}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Mission Note */}
          <div className="about-motto-box">
            <span>Built for understanding contracts with clarity and confidence.</span>
          </div>

          {/* Disclaimer */}
          <div className="about-disclaimer-box">
            <AlertCircle size={15} />
            <p>
              Term Shield provides AI-assisted contract analysis for informational purposes and does not constitute legal advice.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* =========================
   PLACEHOLDER PAGE
========================= */

function PlaceholderPage({
  title,
  description,
}) {
  return (
    <div className="placeholder-page">
      <div className="placeholder-icon">
        <FileText size={28} />
      </div>

      <span className="eyebrow">
        COMING NEXT
      </span>

      <h2>{title}</h2>

      <p>{description}</p>
    </div>
  );
}

export default App;