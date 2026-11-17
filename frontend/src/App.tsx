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

export function AppContent() {
  const [currentPage, setCurrentPage] = useState<NavPage>("dashboard");
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [heldOrdersCount, setHeldOrdersCount] = useState<number>(0);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

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

  const handleViewOrder = (orderId: string) => {
    setSelectedOrderId(orderId);
    setCurrentPage("order-details");
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      {/* Modern Enterprise Sidebar Navigation */}
      <Sidebar
        currentPage={currentPage}
        onNavigate={(page) => setCurrentPage(page)}
        heldCount={heldOrdersCount}
        isConnected={isConnected}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Sticky Top Header */}
        <Header
          currentPage={currentPage}
          onNavigate={(page) => setCurrentPage(page)}
          onDataRefresh={() => {
            updateHeldCount();
            setRefreshTrigger((prev) => prev + 1);
          }}
        />

        {/* Dynamic Page Router */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto">
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
