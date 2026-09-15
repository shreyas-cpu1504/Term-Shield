import { useRef, useState } from "react";
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
} from "lucide-react";

import {
  ingestContractUrl,
  uploadContractAudio,
  uploadContractFile,
  uploadContractVideo,
} from "./api/ingestionApi";
import { getContractAnalysis } from "./api/analysisApi";

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

  const [currentFileId, setCurrentFileId] = useState(null);
  const [currentAnalysis, setCurrentAnalysis] = useState(null);

  const activeItem = navigation.find((item) => item.id === activePage);

  const handleNavigation = (id) => {
    setActivePage(id);
    setMobileMenu(false);
  };

  return (
    <div className="app-shell">
      {mobileMenu && (
        <div
          className="sidebar-overlay"
          onClick={() => setMobileMenu(false)}
        />
      )}

      <aside className={`sidebar ${mobileMenu ? "sidebar-open" : ""}`}>
        <div className="sidebar-top">
          <div className="brand">
            <div className="brand-mark">
              <ShieldAlert size={19} strokeWidth={2.2} />
            </div>

            <div className="brand-text">
              <span>Term</span>
              <strong>Shield</strong>
            </div>
          </div>

          <button
            className="mobile-close"
            onClick={() => setMobileMenu(false)}
            type="button"
          >
            <X size={20} />
          </button>
        </div>

        <div className="workspace-label">WORKSPACE</div>

        <nav className="sidebar-nav">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.id;

            return (
              <button
                key={item.id}
                type="button"
                className={`nav-item ${isActive ? "active" : ""}`}
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

          <div className="sidebar-profile">
            <div className="profile-avatar">AR</div>

            <div className="profile-info">
              <strong>Account</strong>
              <span>Personal workspace</span>
            </div>

            <ChevronDown size={16} />
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

            <button className="top-profile" type="button">
              AR
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
                handleNavigation("analysis");
              }}
            />
          )}

          {/* RISK ANALYSIS */}
          {activePage === "analysis" && (
            <RiskAnalysis
              fileId={currentFileId}
              analysis={currentAnalysis}
            />
          )}

          {/* CONTRACTS */}
          {activePage === "contracts" && (
            <ContractsPage
              fileId={currentFileId}
              analysis={currentAnalysis}
              onNavigate={handleNavigation}
            />
          )}

          {/* CLAUSE EXPLORER */}
          {activePage === "clauses" && (
            <ClauseExplorer analysis={currentAnalysis} />
          )}

          {/* OTHER PAGES */}
          {activePage !== "dashboard" &&
            activePage !== "upload" &&
            activePage !== "analysis" &&
            activePage !== "contracts" &&
            activePage !== "clauses" && (
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

            function ClauseExplorer({ analysis }) {
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
                        Search the analyzed language, compare risk signals, and open a
                        clause to understand what it means for you.
                      </p>
                    </div>

                    <div className="clause-explorer-count">
                      <strong>{normalizedClauses.length}</strong>
                      <span>clauses analyzed</span>
                    </div>
                  </section>

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

/* =========================
   CONTRACTS
========================= */

function ContractsPage({
  fileId,
  analysis,
  onNavigate,
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const clauses = Array.isArray(analysis)
    ? analysis
    : analysis?.analyses ||
      analysis?.clauses ||
      analysis?.results ||
      analysis?.data ||
      [];

  const riskLevel = clauses.some(
    (clause) =>
      String(
        clause?.risk_level ||
          clause?.risk ||
          clause?.riskLevel ||
          ""
      ).toLowerCase() === "high"
  )
    ? "high"
    : clauses.some(
        (clause) =>
          String(
            clause?.risk_level ||
              clause?.risk ||
              clause?.riskLevel ||
              ""
          ).toLowerCase() === "medium"
      )
      ? "medium"
      : clauses.length
        ? "low"
        : "unrated";

  const contractName =
    analysis?.filename ||
    analysis?.file_name ||
    "Latest analyzed contract";

  const contractType =
    analysis?.file_type ||
    contractName.split(".").pop() ||
    "document";

  const createdAt = analysis?.created_at || analysis?.updated_at;
  const contractDate = createdAt
    ? new Date(createdAt).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Latest upload";

  const contracts = fileId
    ? [
        {
          id: fileId,
          name: contractName,
          type: String(contractType).toUpperCase(),
          date: contractDate,
          status: "Analyzed",
          risk: riskLevel,
        },
      ]
    : [];

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
              onClick={() => onNavigate("analysis")}
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