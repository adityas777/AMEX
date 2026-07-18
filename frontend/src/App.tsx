import { useState, useEffect, useCallback } from "react";
import type { CardMember, Claim, EntitlementBalance } from "./types";
import { Dashboard } from "./components/Dashboard";
import { ClaimFeed } from "./components/ClaimFeed";
import { ClaimDetail } from "./components/ClaimDetail";
import { AdminDashboard } from "./components/AdminDashboard";
import { SimulatorControls } from "./components/SimulatorControls";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [members, setMembers] = useState<CardMember[]>([]);
  const [activeMemberId, setActiveMemberId] = useState<string>("");
  const [claims, setClaims] = useState<Claim[]>([]);
  const [allClaims, setAllClaims] = useState<Claim[]>([]); // for Admin dashboard
  const [entitlements, setEntitlements] = useState<EntitlementBalance[]>([]);
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);
  const [activeTab, setActiveTab] = useState<"customer" | "admin">("customer");
  const [logs, setLogs] = useState<string[]>([]);

  const addLog = useCallback((message: string, type: "info" | "warn" | "error" | "success" = "info") => {
    const timestamp = new Date().toLocaleTimeString();
    const prefix = `[${timestamp}] [${type.toUpperCase()}]`;
    setLogs((prev) => [`${prefix} ${message}`, ...prev].slice(0, 100));
  }, []);

  // Fetch cardholders
  useEffect(() => {
    const fetchMembers = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/card-members`);
        if (!res.ok) throw new Error("Failed to fetch card members");
        const data = await res.json();
        setMembers(data);
        if (data.length > 0) {
          setActiveMemberId(data[0].id);
        }
        addLog("Engine connected. Loaded cardholders.", "success");
      } catch (err) {
        addLog(`Backend connection failed. Is the API running?`, "error");
      }
    };
    fetchMembers();
  }, [addLog]);

  // Fetch entitlements & claims for active cardholder
  const fetchMemberData = useCallback(async (memberId: string) => {
    if (!memberId) return;
    try {
      // 1. Fetch entitlements
      const entRes = await fetch(`${API_BASE_URL}/card-members/${memberId}/entitlement-summary`);
      if (entRes.ok) {
        const entData = await entRes.json();
        setEntitlements(entData.balances);
      }

      // 2. Fetch active claims
      const clmRes = await fetch(`${API_BASE_URL}/card-members/${memberId}/detected-benefits`);
      if (clmRes.ok) {
        const clmData = await clmRes.json();
        // Sort claims by creation date (newest first)
        const sorted = clmData.sort(
          (a: Claim, b: Claim) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setClaims(sorted);
      }
    } catch (err) {
      addLog(`Error fetching member details for ${memberId}`, "error");
    }
  }, [addLog]);

  // Fetch all claims in system for Admin dashboard
  const fetchAllClaims = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/admin/claims`);
      if (res.ok) {
        const data = await res.json();
        const sorted = data.sort(
          (a: Claim, b: Claim) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setAllClaims(sorted);
      }
    } catch (err) {
      console.error(err);
    }
  }, []);

  // Sync member details
  useEffect(() => {
    if (activeMemberId) {
      fetchMemberData(activeMemberId);
    }
  }, [activeMemberId, fetchMemberData]);

  // Sync admin dashboard when tab changes
  useEffect(() => {
    if (activeTab === "admin") {
      fetchAllClaims();
    }
  }, [activeTab, fetchAllClaims]);

  const handleSelectMember = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value;
    setActiveMemberId(id);
    setSelectedClaim(null);
    addLog(`Switched active card member to: ${id}`, "info");
  };

  const activeMember = members.find((m) => m.id === activeMemberId);

  // Submit Claim (Customer View)
  const handleSubmitClaim = async (claimId: string, preFilledFields: any) => {
    try {
      addLog(`Submitting claim application ${claimId} with evidence...`, "info");
      const res = await fetch(`${API_BASE_URL}/claims/${claimId}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pre_filled_fields: preFilledFields }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Submission failed");
      }

      const updatedClaim = await res.json();
      addLog(`Claim ${claimId} successfully submitted to underwriting queue!`, "success");
      
      // Refresh
      await fetchMemberData(activeMemberId);
      await fetchAllClaims();
      setSelectedClaim(updatedClaim);
    } catch (err: any) {
      addLog(`Claim submission failed: ${err.message}`, "error");
    }
  };

  // Update claim status (Admin View)
  const handleAdminUpdateStatus = async (claimId: string, status: string) => {
    try {
      addLog(`Admin action: Updating claim ${claimId} status to ${status.toUpperCase()}...`, "info");
      const res = await fetch(`${API_BASE_URL}/claims/${claimId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Status update failed");
      }

      addLog(`Claim ${claimId} status updated to ${status.toUpperCase()}`, "success");
      
      // Refresh states
      await fetchAllClaims();
      await fetchMemberData(activeMemberId);
    } catch (err: any) {
      addLog(`Underwriting action failed: ${err.message}`, "error");
    }
  };

  // Run Simulator Scenario
  const handleRunScenario = async (scenarioType: string) => {
    if (!activeMemberId) return;
    try {
      addLog(`Publishing mock stream for scenario: ${scenarioType.toUpperCase()}...`, "warn");
      const res = await fetch(`${API_BASE_URL}/simulator/run-scenario`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scenario_type: scenarioType,
          card_member_id: activeMemberId,
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to trigger scenario");
      }

      const data = await res.json();
      
      addLog(`[TX STREAM] Ingested transaction ${data.transaction_id}`, "success");
      addLog(`[EVENT STREAM] Published trigger event ${data.event_id}`, "success");
      addLog(`[ENGINE] Run evaluations: Claim ${data.claim_id} AUTO-DETECTED`, "success");

      // Refresh
      await fetchMemberData(activeMemberId);
      await fetchAllClaims();
    } catch (err: any) {
      addLog(`Simulation failure: ${err.message}`, "error");
    }
  };

  // Reset database
  const handleResetDb = async () => {
    try {
      addLog("Resetting database to initial seeds...", "warn");
      const res = await fetch(`${API_BASE_URL}/simulator/reset-db`, {
        method: "POST",
      });
      if (res.ok) {
        addLog("Database reset. Seeding default Amex Platinum & Gold members completed.", "success");
        setSelectedClaim(null);
        if (members.length > 0) {
          // Trigger reload of default first member
          fetchMemberData(activeMemberId);
          fetchAllClaims();
        }
      }
    } catch (err) {
      addLog("Database reset failed.", "error");
    }
  };

  // Sync from Gmail
  const handleSyncGmail = async () => {
    try {
      addLog("Querying Gmail inbox for unread transaction & flight-delay alerts...", "warn");
      const res = await fetch(`${API_BASE_URL}/gmail/poll-now`, {
        method: "POST",
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Gmail sync failed");
      }

      const data = await res.json();
      const results = data.data;

      addLog(`[GMAIL SYNC] Ingested ${results.transactions_ingested} transactions and ${results.events_ingested} flight delays. Skipped ${results.skipped} duplicates.`, "success");

      // Refresh data
      await fetchMemberData(activeMemberId);
      await fetchAllClaims();
    } catch (err: any) {
      addLog(`Gmail Sync failed: ${err.message}`, "error");
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header>
        <div className="logo-container">
          <div className="amex-box">AMEX</div>
          <div className="logo-text">Card Benefit Activation Engine</div>
        </div>

        <div className="header-controls">
          <div className="nav-tabs">
            <button
              className={`nav-tab ${activeTab === "customer" ? "active" : ""}`}
              onClick={() => setActiveTab("customer")}
            >
              Cardholder View
            </button>
            <button
              className={`nav-tab ${activeTab === "admin" ? "active" : ""}`}
              onClick={() => setActiveTab("admin")}
            >
              Admin Ops Portal
            </button>
          </div>

          <div className="member-select-wrapper">
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>Cardholder:</span>
            <select
              className="custom-select"
              value={activeMemberId}
              onChange={handleSelectMember}
            >
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.id})
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {/* Main Grid Body */}
      <div className="main-content">
        <div className="dashboard-grid">
          {activeTab === "customer" ? (
            <>
              {activeMember && (
                <Dashboard
                  memberName={activeMember.name}
                  cardProduct={activeMember.card_product}
                  entitlements={entitlements}
                />
              )}
              {selectedClaim ? (
                <ClaimDetail
                  claim={selectedClaim}
                  onSubmitClaim={handleSubmitClaim}
                  onClose={() => setSelectedClaim(null)}
                />
              ) : (
                <ClaimFeed
                  claims={claims}
                  selectedClaimId={null}
                  onSelectClaim={(claim) => setSelectedClaim(claim)}
                />
              )}
            </>
          ) : (
            <AdminDashboard
              claims={allClaims}
              onUpdateStatus={handleAdminUpdateStatus}
            />
          )}
        </div>

        {/* Right Sidebar Simulator Controls */}
        <SimulatorControls
          cardholderId={activeMemberId}
          logs={logs}
          onRunScenario={handleRunScenario}
          onResetDb={handleResetDb}
          onSyncGmail={handleSyncGmail}
        />
      </div>
    </div>
  );
}

export default App;
