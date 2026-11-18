import { useState, useEffect, useCallback } from "react";
import { ThemeProvider } from "./context/ThemeContext";
import { Sidebar } from "./components/layout/Sidebar";
import type { NavPage } from "./components/layout/Sidebar";
import { Header } from "./components/layout/Header";
import { DashboardPage } from "./pages/DashboardPage";
import { CreateOrderPage } from "./pages/CreateOrderPage";
import { OrderManagementPage } from "./pages/OrderManagementPage";
import { AgentMonitoringPage } from "./pages/AgentMonitoringPage";
import { FraudReviewPage } from "./pages/FraudReviewPage";
import { OrderDetailsPage } from "./pages/OrderDetailsPage";
import { useOrderWebSocket } from "./hooks/useOrderWebSocket";
import { fetchHeldOrders } from "./api";

function getInitialRoute(): { page: NavPage; orderId: string | null } {
  if (typeof window === "undefined") return { page: "dashboard", orderId: null };
  const params = new URLSearchParams(window.location.search);
  const queryPage = params.get("page") as NavPage | null;
  const queryId = params.get("id");
  if (queryPage && ["dashboard", "create-order", "orders", "agents", "fraud-review", "order-details"].includes(queryPage)) {
    return { page: queryPage, orderId: queryId };
  }
  const hash = window.location.hash.replace("#/", "").replace("#", "");
  if (hash.startsWith("order-details")) {
    const queryIdx = hash.indexOf("?id=");
    const id = queryIdx !== -1 ? hash.substring(queryIdx + 4) : null;
    return { page: "order-details", orderId: id };
  }
  if (["dashboard", "create-order", "orders", "agents", "fraud-review", "order-details"].includes(hash)) {
    return { page: hash as NavPage, orderId: null };
  }
  return { page: "dashboard", orderId: null };
}

export function AppContent() {
  const initial = getInitialRoute();
  const [currentPage, setCurrentPage] = useState<NavPage>(initial.page);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(initial.orderId);
  const [heldOrdersCount, setHeldOrdersCount] = useState<number>(0);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  // Route listener for deep-linking (supporting both query params and hash routes)
  useEffect(() => {
    const syncRoute = () => {
      // Check query parameters first (?page=...&id=...)
      const params = new URLSearchParams(window.location.search);
      const queryPage = params.get("page");
      const queryId = params.get("id");
      if (queryId) {
        setSelectedOrderId(queryId);
      }
      if (queryPage && ["dashboard", "create-order", "orders", "agents", "fraud-review", "order-details"].includes(queryPage)) {
        setCurrentPage(queryPage as NavPage);
        return;
      }

      // Check hash route fallback (#/page or #page)
      const hash = window.location.hash.replace("#/", "").replace("#", "");
      if (hash.startsWith("order-details")) {
        setCurrentPage("order-details");
        const queryIdx = hash.indexOf("?id=");
        if (queryIdx !== -1) {
          const id = hash.substring(queryIdx + 4);
          if (id) setSelectedOrderId(id);
        }
      } else if (
        ["dashboard", "create-order", "orders", "agents", "fraud-review", "order-details"].includes(hash)
      ) {
        setCurrentPage(hash as NavPage);
      }
    };
    syncRoute();
    window.addEventListener("hashchange", syncRoute);
    window.addEventListener("popstate", syncRoute);
    return () => {
      window.removeEventListener("hashchange", syncRoute);
      window.removeEventListener("popstate", syncRoute);
    };
  }, []);

  // Poll / update held orders count for sidebar badge
  const updateHeldCount = useCallback(async () => {
    try {
      const held = await fetchHeldOrders();
      setHeldOrdersCount(held.length);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    updateHeldCount();
  }, [updateHeldCount, refreshTrigger]);

  // Live WebSocket integration
  const { isConnected } = useOrderWebSocket(
    useCallback(() => {
      // Whenever an order is processed, overridden or rejected via WebSocket, refresh counts
      updateHeldCount();
      setRefreshTrigger((prev) => prev + 1);
    }, [updateHeldCount])
  );

  const handleNavigate = (page: NavPage) => {
    setCurrentPage(page);
    window.location.hash = `#/${page}`;
  };

  const handleViewOrder = (orderId: string) => {
    setSelectedOrderId(orderId);
    setCurrentPage("order-details");
    window.location.hash = `#/order-details?id=${orderId}`;
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      {/* Modern Enterprise Sidebar Navigation */}
      <Sidebar
        currentPage={currentPage}
        onNavigate={handleNavigate}
        heldCount={heldOrdersCount}
        isConnected={isConnected}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Sticky Top Header */}
        <Header
          currentPage={currentPage}
          onNavigate={handleNavigate}
          onDataRefresh={() => {
            updateHeldCount();
            setRefreshTrigger((prev) => prev + 1);
          }}
        />

        {/* Dynamic Page Router */}
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="w-full max-w-[1750px] mx-auto space-y-6">
            {currentPage === "dashboard" && (
              <DashboardPage
                key={refreshTrigger}
                onViewOrder={handleViewOrder}
                onNavigateToFraud={() => setCurrentPage("fraud-review")}
              />
            )}

            {currentPage === "create-order" && (
              <CreateOrderPage
                onOrderCreated={() => {
                  updateHeldCount();
                  setRefreshTrigger((prev) => prev + 1);
                }}
                onViewOrderDetails={handleViewOrder}
              />
            )}

            {currentPage === "orders" && (
              <OrderManagementPage
                key={refreshTrigger}
                onViewOrder={handleViewOrder}
                onNavigateToCreate={() => setCurrentPage("create-order")}
              />
            )}

            {currentPage === "agents" && (
              <AgentMonitoringPage key={refreshTrigger} />
            )}

            {currentPage === "fraud-review" && (
              <FraudReviewPage
                key={refreshTrigger}
                onViewOrderDetails={handleViewOrder}
                onRefreshMetrics={() => {
                  updateHeldCount();
                  setRefreshTrigger((prev) => prev + 1);
                }}
              />
            )}

            {currentPage === "order-details" && (
              <OrderDetailsPage
                key={selectedOrderId || "empty"}
                orderId={selectedOrderId}
                onBack={() => setCurrentPage("orders")}
                onSelectOrder={(id) => setSelectedOrderId(id)}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
