import { useEffect, useRef, useState } from "react";
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
import { askContractQuestion } from "./api/qaApi";
import { getCurrentUser } from "./api/authApi";
import { getContracts } from "./api/contractsApi";
import Login from "./components/Login";
import Register from "./components/Register";

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

function App() {
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
    fetchCurrentUser().catch(() => {});
  };

  const handleRegisterSuccess = () => {
    setAuthState("authenticated");
    fetchCurrentUser().catch(() => {});
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

  if (authState === "checking") {
    return (
      <main
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          background: "#f6f6f8",
          color: "#85858e",
          fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
          fontSize: "12px",
        }}
      >
        Checking your workspace...
      </main>
    );
  }

  if (authState === "unauthenticated") {
    const isLoginScreen = authScreen === "login";

    return (
      <div style={{ position: "relative", minHeight: "100vh" }}>
        {isLoginScreen ? (
          <Login onLoginSuccess={handleLoginSuccess} />
        ) : (
          <Register onRegisterSuccess={handleRegisterSuccess} />
        )}

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
            color: "#85827b",
            fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
            fontSize: "10px",
          }}
        >
          <span>
            {isLoginScreen
              ? "New to Term Shield?"
              : "Already have an account?"}
          </span>
          <button
            type="button"
            onClick={() => setAuthScreen(isLoginScreen ? "register" : "login")}
            style={{
              padding: "4px 0",
              border: 0,
              background: "transparent",
              color: "#986a37",
              font: "inherit",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            {isLoginScreen ? "Create account" : "Sign in"}
          </button>
        </div>
      </div>
    );
  }

  const userInitials = currentUser?.full_name
    ? currentUser.full_name
        .trim()
        .split(/\s+/)
        .map((part) => part[0]?.toUpperCase())
        .slice(0, 2)
        .join("") || "TS"
    : currentUser?.email
    ? currentUser.email.slice(0, 2).toUpperCase()
    : "TS";

  const userDisplayName =
    currentUser?.full_name?.trim() || currentUser?.email || "Account";

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
            className={`nav-item ${
              activePage === "settings" ? "active" : ""
            }`}
            onClick={() => handleNavigation("settings")}
          >
            <Settings size={18} />
            <span>Settings</span>
          </button>

          <button
            className="sidebar-profile"
            type="button"
            onClick={() => handleNavigation("settings")}
            aria-label="Account Settings"
            title="Open Settings"
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
            <div className="profile-avatar">{userInitials}</div>

            <div className="profile-info">
              <strong>{userDisplayName}</strong>
              <span>{currentUser?.email || "Personal workspace"}</span>
            </div>

            <ChevronDown size={16} />
          </button>
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
              className={`ask-button ${
                activePage === "ask" ? "active" : ""
              }`}
              type="button"
              onClick={() => handleNavigation("ask")}
              aria-label="Ask My T&C"
            >
              <MessageSquare size={16} />
              <span>Ask My T&C</span>
            </button>

            <div className="search-box">
              <Search size={17} />
              <input placeholder="Search contracts..." />
              <kbd>⌘ K</kbd>
            </div>

            <button className="icon-button" type="button">
              <Bell size={18} />
              <span className="notification-dot" />
            </button>

            <button
              className="top-profile"
              type="button"
              onClick={() => handleNavigation("settings")}
              title="Open Settings"
              aria-label="User Settings"
            >
              {userInitials}
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

          {/* CONTRACT SUMMARY */}
          {activePage === "reports" && (
            <ContractSummary
              fileId={currentFileId}
              analysis={currentAnalysis}
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
                              className={`clause-explorer-item ${
                                selectedClause?.id === clause.id ? "selected" : ""
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

              const matched = clausesList.find((c) => {
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

            function ClauseRelationships({ fileId, clauses = [], onSelectClause }) {
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

                    // 4. Verify returned data.file_id matches current fileId
                    if (data && (String(data.file_id) === String(fileId) || !data.file_id)) {
                      setRelationshipsData(data);
                    } else {
                      console.warn("Mismatched relationship data file_id:", data?.file_id, "expected:", fileId);
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
                    if (data && (String(data.file_id) === String(fileId) || !data.file_id)) {
                      setRelationshipsData(data);
                    }
                    setLoading(false);
                  })
                  .catch((err) => {
                    setError(err?.response?.data?.detail || "Unable to load clause relationships.");
                    setLoading(false);
                  });
              };

              const rawRelationships = relationshipsData?.relationships || [];

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
                if (!searchQuery.trim()) return true;
                const q = searchQuery.toLowerCase();
                const src = resolveClauseData(r.source_clause_id, clauses);
                const tgt = resolveClauseData(r.target_clause_id, clauses);
                return (
                  (r.relationship_type && r.relationship_type.toLowerCase().includes(q)) ||
                  (r.evidence && r.evidence.toLowerCase().includes(q)) ||
                  (src?.title && src.title.toLowerCase().includes(q)) ||
                  (tgt?.title && tgt.title.toLowerCase().includes(q))
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

              const graphNodes = uniqueNodeIds.map((id) => resolveClauseData(id, clauses));

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

              // Selected relationship or node
              const selectedRel =
                selectedRelIndex !== null && visibleRelationships[selectedRelIndex]
                  ? visibleRelationships[selectedRelIndex]
                  : null;

              const selectedNode =
                selectedNodeId ? resolveClauseData(selectedNodeId, clauses) : null;

              const selectedNodeRels = selectedNode
                ? rawRelationships.filter(
                    (r) =>
                      r.source_clause_id === selectedNode.id ||
                      r.target_clause_id === selectedNode.id
                  )
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
                                  markerWidth="6"
                                  markerHeight="6"
                                  orient="auto-start-reverse"
                                >
                                  <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill={cfg.color} />
                                </marker>
                              ))}
                              <filter id="rel-glow" x="-20%" y="-20%" width="140%" height="140%">
                                <feDropShadow dx="0" dy="1" stdDeviation="2" floodColor="#8f744f" floodOpacity="0.3" />
                              </filter>
                            </defs>

                            {/* Center circle guide */}
                            <g opacity="0.25">
                              <circle cx={cx} cy={cy} r={rx} fill="none" stroke="#e2ddd4" strokeDasharray="3,6" />
                            </g>

                            {/* Connection Edges */}
                            {visibleRelationships.map((rel, idx) => {
                              const src = nodeCoords[rel.source_clause_id];
                              const tgt = rel.target_clause_id ? nodeCoords[rel.target_clause_id] : null;
                              const typeKey = (rel.relationship_type || "REFERENCE").toUpperCase();
                              const cfg = RELATIONSHIP_TYPES[typeKey] || RELATIONSHIP_TYPES.REFERENCE;

                              if (!src) return null;

                              let pathD = "";
                              if (tgt && rel.source_clause_id !== rel.target_clause_id) {
                                const midX = (src.x + tgt.x) / 2;
                                const midY = (src.y + tgt.y) / 2;
                                const cpx = midX + (cx - midX) * 0.42;
                                const cpy = midY + (cy - midY) * 0.42;

                                const dx = tgt.x - cpx;
                                const dy = tgt.y - cpy;
                                const dist = Math.hypot(dx, dy) || 1;
                                const endX = tgt.x - (dx / dist) * 26;
                                const endY = tgt.y - (dy / dist) * 26;

                                pathD = `M ${src.x} ${src.y} Q ${cpx} ${cpy} ${endX} ${endY}`;
                              } else {
                                const nx = Math.cos(src.angle) * 45;
                                const ny = Math.sin(src.angle) * 45;
                                pathD = `M ${src.x - 14} ${src.y} C ${src.x + nx - 20} ${src.y + ny - 20}, ${src.x + nx + 20} ${src.y + ny + 20}, ${src.x + 14} ${src.y}`;
                              }

                              const isSelected = selectedRelIndex === idx;
                              const isConnectedToSelectedNode =
                                selectedNodeId &&
                                (rel.source_clause_id === selectedNodeId ||
                                  rel.target_clause_id === selectedNodeId);
                              const isHighlighted = isSelected || isConnectedToSelectedNode;
                              const isDimmed =
                                (selectedRelIndex !== null || selectedNodeId !== null) &&
                                !isHighlighted;

                              return (
                                <g key={`edge-${idx}`} className="clause-rel-edge-group">
                                  {/* Transparent wide stroke for easy clicking/hover */}
                                  <path
                                    d={pathD}
                                    fill="none"
                                    stroke="transparent"
                                    strokeWidth="18"
                                    style={{ cursor: "pointer" }}
                                    onClick={() => {
                                      setSelectedRelIndex(idx);
                                      setSelectedNodeId(null);
                                    }}
                                  />
                                  {/* Visible stroke */}
                                  <path
                                    d={pathD}
                                    fill="none"
                                    stroke={cfg.color}
                                    strokeWidth={isHighlighted ? 3.2 : 1.8}
                                    strokeDasharray={cfg.dashed ? "5,4" : "none"}
                                    opacity={isDimmed ? 0.14 : isHighlighted ? 1 : 0.72}
                                    markerEnd={`url(#rel-arrow-${typeKey})`}
                                    style={{
                                      transition: "stroke-width 0.2s, opacity 0.2s",
                                      pointerEvents: "none",
                                    }}
                                  />
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
                                  className={`clause-rel-node ${isHighlighted ? "highlighted" : ""} ${
                                    isDimmed ? "dimmed" : ""
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
                              const tgt = resolveClauseData(selectedRel.target_clause_id, clauses);
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
                                    const otherId = isOutgoing ? rel.target_clause_id : rel.source_clause_id;
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
                                          "{rel.evidence?.slice(0, 110)}..."
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
                                {visibleRelationships.map((rel, idx) => {
                                  const src = resolveClauseData(rel.source_clause_id, clauses);
                                  const tgt = resolveClauseData(rel.target_clause_id, clauses);
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
                                        "{rel.evidence?.slice(0, 95)}..."
                                      </small>
                                    </button>
                                  );
                                })}
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
               CONTRACT SUMMARY
            ========================= */

            function ContractSummary({ fileId, analysis }) {
              const [backendSummary, setBackendSummary] = useState(null);
              const [summaryLoading, setSummaryLoading] = useState(false);
              const [summaryError, setSummaryError] = useState("");

              useEffect(() => {
                if (!fileId) {
                  setBackendSummary(null);
                  setSummaryLoading(false);
                  setSummaryError("");
                  return undefined;
                }

                let cancelled = false;

                setBackendSummary(null);
                setSummaryLoading(true);
                setSummaryError("");

                getContractSummary(fileId)
                  .then((data) => {
                    if (!cancelled) {
                      setBackendSummary(data);
                    }
                  })
                  .catch((error) => {
                    if (!cancelled) {
                      setSummaryError(
                        error?.response?.data?.detail ||
                          error?.response?.data?.message ||
                          error?.message ||
                          "Unable to load contract summary."
                      );
                    }
                  })
                  .finally(() => {
                    if (!cancelled) {
                      setSummaryLoading(false);
                    }
                  });

                return () => {
                  cancelled = true;
                };
              }, [fileId]);

              const summaryMatchesContract = backendSummary?.file_id === fileId;
              const currentSummary = summaryMatchesContract ? backendSummary : null;

              const clauses = Array.isArray(analysis)
                ? analysis
                : analysis?.analyses ||
                  analysis?.clauses ||
                  analysis?.results ||
                  analysis?.data ||
                  [];

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

              const contractName =
                analysis?.filename ||
                analysis?.file_name ||
                analysis?.contract_name ||
                analysis?.title ||
                (fileId ? "Analyzed contract" : "No contract selected");

              const plainSummary =
                currentSummary?.summary_points ||
                currentSummary?.summary ||
                analysis?.summary ||
                analysis?.plain_language_summary ||
                analysis?.summary_text ||
                (Array.isArray(analysis?.summary_points)
                  ? analysis.summary_points
                  : []);

              const sections = [
                {
                  id: "parties",
                  title: "Key parties and entities",
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
                  title: "Important obligations",
                  icon: ListChecks,
                  items: [
                    ...new Set([
                      ...collectValues(["obligations", "duties"]),
                      ...(Array.isArray(currentSummary?.key_obligations)
                        ? currentSummary.key_obligations
                        : []),
                    ]),
                  ],
                },
                {
                  id: "rights",
                  title: "Important rights",
                  icon: ShieldAlert,
                  items: [
                    ...new Set([
                      ...collectValues(["rights", "permissions"]),
                      ...(Array.isArray(currentSummary?.key_rights)
                        ? currentSummary.key_rights
                        : []),
                    ]),
                  ],
                },
                {
                  id: "conditions",
                  title: "Conditions",
                  icon: FileText,
                  items: collectValues(["conditions", "triggers", "exceptions"]),
                },
                {
                  id: "financial",
                  title: "Financial terms",
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
                      ...(Array.isArray(currentSummary?.monetary_terms)
                        ? currentSummary.monetary_terms
                        : []),
                    ]),
                  ],
                },
                {
                  id: "dates",
                  title: "Important dates and deadlines",
                  icon: CalendarDays,
                  items: [
                    ...new Set([
                      ...collectValues(["dates", "deadlines", "durations"]),
                      ...(Array.isArray(currentSummary?.deadlines)
                        ? currentSummary.deadlines
                        : []),
                    ]),
                  ],
                },
              ];

              const hasSummary = Boolean(
                fileId || clauses.length || (plainSummary && plainSummary.length)
              );

              return (
                <div className="contract-summary-page">
                  <section className="contract-summary-header">
                    <div>
                      <span className="eyebrow">CONTRACT SUMMARY</span>
                      <h2>{contractName}</h2>
                      <p>
                        A plain-language view of the people, commitments, and terms
                        found in the selected contract.
                      </p>
                    </div>

                    <div className="contract-summary-id">
                      <span>CONTRACT ID</span>
                      <strong>{fileId || "Unavailable"}</strong>
                    </div>
                  </section>

                  {!hasSummary ? (
                    <section className="contract-summary-empty">
                      <div className="contract-summary-empty-icon">
                        <FileText size={25} />
                      </div>
                      <span className="card-label">NO CONTRACT SELECTED</span>
                      <h3>Your contract summary will appear here.</h3>
                      <p>
                        Upload and analyze a contract to see its plain-language summary,
                        parties, obligations, rights, and key terms.
                      </p>
                    </section>
                  ) : (
                    <>
                      <section className="contract-summary-overview">
                        <div className="section-kicker">
                          <Sparkles size={14} />
                          PLAIN-LANGUAGE OVERVIEW
                        </div>

                        {summaryLoading ? (
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "8px",
                              marginTop: "15px",
                              color: "#85827b",
                              fontSize: "12px",
                            }}
                          >
                            <Loader2 size={16} className="spin" />
                            <span>Loading plain-language summary...</span>
                          </div>
                        ) : summaryError ? (
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "8px",
                              marginTop: "15px",
                              color: "#c2410c",
                              fontSize: "12px",
                            }}
                            role="alert"
                          >
                            <AlertCircle size={16} />
                            <span>{summaryError}</span>
                          </div>
                        ) : plainSummary?.length ? (
                          Array.isArray(plainSummary) ? (
                            <ul>
                              {plainSummary.map((point, index) => (
                                <li key={index}>{point}</li>
                              ))}
                            </ul>
                          ) : (
                            <p>{plainSummary}</p>
                          )
                        ) : (
                          <p className="summary-unavailable">
                            A plain-language summary was not returned for this contract.
                          </p>
                        )}
                      </section>

                      <section className="contract-summary-grid">
                        {sections.map((section) => (
                          <SummarySection key={section.id} {...section} />
                        ))}
                      </section>
                    </>
                  )}
                </div>
              );
            }

            function SummarySection({ title, icon: Icon, items }) {
              return (
                <section className="summary-section">
                  <div className="summary-section-heading">
                    <div className="summary-section-icon">
                      <Icon size={17} />
                    </div>
                    <div>
                      <span className="card-label">CONTRACT INTELLIGENCE</span>
                      <h3>{title}</h3>
                    </div>
                  </div>

                  {items.length ? (
                    <ul>
                      {items.map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="summary-section-empty">No information available.</div>
                  )}
                </section>
              );
            }

            /* =========================
               ASK MY T&C
            ========================= */

            function AskMyTC({ fileId, analysis }) {
              const [draft, setDraft] = useState("");
              const [messages, setMessages] = useState([]);
              const [isAsking, setIsAsking] = useState(false);
              const [qaError, setQaError] = useState("");

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

              const handleSend = async () => {
                const question = draft.trim();
                if (!question || !hasContract || isAsking) return;

                setMessages((currentMessages) => [
                  ...currentMessages,
                  { id: `${Date.now()}-user`, role: "user", text: question },
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
                        <span>{hasContract ? "Contract context ready" : "Waiting for a contract"}</span>
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
                            {hasContract
                              ? `I’m ready to help you understand ${contractName}. Ask about a clause, obligation, deadline, or risk signal.`
                              : "Upload and analyze a contract first, then I can help you explore its terms in plain language."}
                          </div>
                        </div>
                      </div>

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
                            <div className="ask-message-bubble">{message.text}</div>
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
                    </div>

                    <div className="ask-chat-composer">
                      <div className="ask-suggestions">
                        <span>Try asking</span>
                        <div>
                          {suggestedQuestions.map((question) => (
                            <button
                              type="button"
                              key={question}
                              disabled={!hasContract || isAsking}
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
                          disabled={!hasContract || isAsking}
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
                          disabled={!hasContract || !draft.trim() || isAsking}
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
                        Answers are grounded in the selected contract.
                      </p>
                    </div>
                  </section>
                </div>
              );
            }

/* =========================
   DASHBOARD
========================= */

function Dashboard({ onNavigate, fileId, analysis }) {
  const clauses = Array.isArray(analysis)
    ? analysis
    : analysis?.analyses ||
      analysis?.clauses ||
      analysis?.results ||
      analysis?.data ||
      [];

  const riskCounts = clauses.reduce(
    (counts, clause) => {
      const risk = String(
        clause?.risk_level ||
          clause?.risk ||
          clause?.riskLevel ||
          ""
      ).toLowerCase();

      if (risk === "high") counts.high += 1;
      if (risk === "medium") counts.medium += 1;
      if (risk === "low") counts.low += 1;

      return counts;
    },
    { high: 0, medium: 0, low: 0 }
  );

  const hasContract = Boolean(fileId);
  const hasAnalysis = clauses.length > 0;
  const totalRiskClauses =
    riskCounts.high + riskCounts.medium + riskCounts.low;
  const riskTotal = Math.max(totalRiskClauses, 1);

  return (
    <div className="dashboard">
      <section className="welcome-section">
        <div className="welcome-copy">
          <span className="eyebrow">
            AI CONTRACT INTELLIGENCE
          </span>

          <h2>
            Good morning.
            <br />
            <span>Make every contract clearer.</span>
          </h2>

          <p>
            Your contract workspace at a glance. Review risk,
            track important terms and turn dense legal language
            into decisions you can act on.
          </p>
        </div>

        <div className="welcome-actions">
          <span className="workspace-status">
            <span className="status-dot" />
            Workspace ready
          </span>

          <button
            className="primary-button"
            type="button"
            onClick={() => onNavigate("upload")}
          >
            <Upload size={17} />
            Upload contract
          </button>
        </div>
      </section>

      <section className="stats-grid">
        <StatCard
          label="Contracts analyzed"
          value={hasContract ? "1" : "0"}
          detail={hasContract ? "Latest workspace activity" : "Start your library"}
          icon={FileText}
        />

        <StatCard
          label="Clauses detected"
          value={clauses.length}
          detail={hasAnalysis ? "Across latest analysis" : "Appears after analysis"}
          icon={ShieldAlert}
        />

        <StatCard
          label="High-risk clauses"
          value={riskCounts.high}
          detail={riskCounts.high ? "Needs your attention" : "No high-risk items yet"}
          icon={ListChecks}
          danger={riskCounts.high > 0}
        />

        <StatCard
          label="Low-risk clauses"
          value={riskCounts.low}
          detail={hasAnalysis ? "Lower concern" : "Appears after analysis"}
          icon={CheckCircle2}
        />
      </section>

      <section className="dashboard-grid dashboard-primary-grid">
        <div className="dashboard-card upload-panel dashboard-feature-card">
          <div className="card-heading">
            <div>
              <span className="card-label">NEXT STEP</span>
              <h3>Bring a contract into focus</h3>
            </div>

            <div className="card-icon feature-icon">
              <Upload size={19} />
            </div>
          </div>

          <p>
            Upload a document or paste a public contract URL.
            Term Shield will surface the clauses, obligations,
            deadlines and financial terms worth your attention.
          </p>

          <div className="upload-benefits">
            <div>
              <CheckCircle2 size={15} />
              <span>Plain-language findings</span>
            </div>
            <div>
              <CheckCircle2 size={15} />
              <span>Risk and obligation signals</span>
            </div>
          </div>

          <button
            className="secondary-button feature-action"
            type="button"
            onClick={() => onNavigate("upload")}
          >
            <Upload size={15} />
            Upload contract
          </button>
        </div>

        <div className="dashboard-card risk-overview-card">
          <div className="card-heading">
            <div>
              <span className="card-label">RISK OVERVIEW</span>
              <h3>Review priority</h3>
            </div>

            <div className="card-icon purple">
              <ShieldAlert size={19} />
            </div>
          </div>

          {hasAnalysis ? (
            <>
              <div className="risk-meter" aria-label="Risk distribution">
                <span
                  className="risk-meter-high"
                  style={{ width: `${(riskCounts.high / riskTotal) * 100}%` }}
                />
                <span
                  className="risk-meter-medium"
                  style={{ width: `${(riskCounts.medium / riskTotal) * 100}%` }}
                />
                <span
                  className="risk-meter-low"
                  style={{ width: `${(riskCounts.low / riskTotal) * 100}%` }}
                />
              </div>

              <div className="risk-summary">
                <div>
                  <strong>{riskCounts.high}</strong>
                  <span>High risk</span>
                </div>
                <div>
                  <strong>{riskCounts.medium}</strong>
                  <span>Medium risk</span>
                </div>
                <div>
                  <strong>{riskCounts.low}</strong>
                  <span>Low risk</span>
                </div>
              </div>

              <p className="risk-overview-note">
                {riskCounts.high > 0
                  ? "Start with high-risk clauses in your latest analysis."
                  : "Your latest analysis has no high-risk clauses."}
              </p>
            </>
          ) : (
            <div className="risk-empty-state">
              <div className="risk-empty-icon">
                <BarChart3 size={18} />
              </div>
              <strong>No risk profile yet</strong>
              <span>Analyze a contract to see review priorities here.</span>
            </div>
          )}

          <button
            className="text-button risk-link"
            type="button"
            onClick={() => onNavigate(hasAnalysis ? "analysis" : "upload")}
          >
            {hasAnalysis ? "Open risk analysis" : "Analyze a contract"} →
          </button>
        </div>
      </section>

      <section className="dashboard-card recent-panel">
        <div className="card-heading">
          <div>
            <span className="card-label">CONTRACT LIBRARY</span>
            <h3>Recent contracts</h3>
          </div>

          <button
            className="text-button"
            type="button"
            onClick={() => onNavigate("contracts")}
          >
            View library →
          </button>
        </div>

        {hasContract ? (
          <div className="recent-contract-row">
            <div className="recent-contract-icon">
              <FileText size={20} />
            </div>

            <div className="recent-contract-info">
              <strong>Latest analyzed contract</strong>
              <span>Contract ID: {fileId}</span>
            </div>

            <span className="contract-status">
              <CheckCircle2 size={14} />
              Analyzed
            </span>

            <button
              className="secondary-button recent-action"
              type="button"
              onClick={() => onNavigate("analysis")}
            >
              View analysis
            </button>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-icon">
              <FileText size={23} />
            </div>

            <h4>Your contract library is ready</h4>

            <p>
              Upload your first contract to see its clauses,
              risks, obligations and AI insights here.
            </p>

            <button
              className="secondary-button"
              type="button"
              onClick={() => onNavigate("upload")}
            >
              <Upload size={15} />
              Upload your first contract
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
          className={`method-tab ${
            activeInput === "file" ? "active" : ""
          }`}
          onClick={() => setActiveInput("file")}
        >
          <FileUp size={17} />
          Upload file
        </button>

        <button
          type="button"
          className={`method-tab ${
            activeInput === "url" ? "active" : ""
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
              className={`large-dropzone ${
                dragging ? "dragging" : ""
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
        className={`stat-icon ${
          danger ? "danger" : ""
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

        {clauses.length === 0 ? (
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
  onNavigate,
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

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
            <button
              className="contract-library-card"
              type="button"
              key={contract.id}
              onClick={() => onSelectContract(contract.id)}
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

              <ChevronDown className="contract-library-arrow" size={18} />
            </button>
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

  const initials = currentUser?.full_name
    ? currentUser.full_name
        .trim()
        .split(/\s+/)
        .map((p) => p[0]?.toUpperCase())
        .slice(0, 2)
        .join("") || "TS"
    : currentUser?.email
    ? currentUser.email.slice(0, 2).toUpperCase()
    : "TS";

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
          <span className="eyebrow">SETTINGS & PREFERENCES</span>
          <h2>Workspace & Account</h2>
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
              <div className="settings-large-avatar">{initials}</div>
              <div className="settings-profile-main">
                <h4>{currentUser.full_name || "Term Shield User"}</h4>
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
                <span className="field-value">{currentUser.full_name || "Not specified"}</span>
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
                <span className="card-label">DATA & ACCESS SECURITY</span>
                <h3>Authentication & Security</h3>
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
                  Default Risk Sensitivity
                  <span className="pref-hint">Adjusts how strict the initial contract risk triage appears</span>
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
                  Clause Explorer Default Layout
                  <span className="pref-hint">Choose how segmented clauses are arranged initially</span>
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
                  Date &amp; Timestamp Display
                  <span className="pref-hint">Format for contract ingestion dates</span>
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
                  <strong>Auto-analyze upon upload</strong>
                  <span>Automatically trigger clause segmentation and risk scoring when a file is ingested</span>
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