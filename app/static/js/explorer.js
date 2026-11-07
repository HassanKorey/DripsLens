(function () {
    console.log("Explorer loaded");

    const tableBody = document.getElementById("events-table-body");
    const emptyState = document.getElementById("empty-state");
    const totalEventsEl = document.getElementById("metric-total-events");
    const statusTextEl = document.getElementById("sse-status-text");

    if (typeof EventSource === "undefined") {
        return;
    }

    const source = new EventSource("/soroban/stream/events");

    source.onmessage = function (event) {
        try {
            const payload = JSON.parse(event.data);
            if (!payload || payload.topic === "ping" && !payload.contract_id) {
                return;
            }
            if (emptyState) {
                emptyState.classList.add("hidden");
            }
            if (tableBody) {
                const row = document.createElement("tr");
                row.className = "hover:bg-slate-50 transition-colors";
                const contractId = payload.contract_id || "C...";
                const topic = payload.topic || "invoke";
                const ledger = payload.ledger_sequence || "-";
                const ts = payload.timestamp || new Date().toISOString();
                row.innerHTML =
                    '<td class="px-6 py-3 font-mono text-xs text-indigo-600">' + contractId + "</td>" +
                    '<td class="px-6 py-3 font-medium text-slate-800">' + topic + "</td>" +
                    '<td class="px-6 py-3 text-slate-600">' + ledger + "</td>" +
                    '<td class="px-6 py-3 text-xs text-slate-500">' + ts + "</td>";
                tableBody.prepend(row);
            }
            if (totalEventsEl) {
                const current = parseInt(totalEventsEl.textContent || "0", 10) || 0;
                totalEventsEl.textContent = String(current + 1);
            }
        } catch (err) {
            console.error("Failed to parse SSE event:", err);
        }
    };

    source.onerror = function () {
        if (statusTextEl) {
            statusTextEl.textContent = "Reconnecting SSE...";
        }
    };
})();
