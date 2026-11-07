/**
 * DripsLens Explorer UI Controls
 * Provides debounced keyword search and live dropdown table filtering without layout jitter.
 */
function debounce(fn, delayMs) {
  let timerId = null;
  return function (...args) {
    if (timerId) {
      clearTimeout(timerId);
    }
    timerId = setTimeout(() => {
      fn.apply(this, args);
    }, delayMs);
  };
}

function applyExplorerFilters() {
  const searchInput = document.getElementById("search-input");
  const complexitySelect = document.getElementById("complexity-filter");
  const topicSelect = document.getElementById("topic-filter");
  const emptyState = document.getElementById("empty-filter-state");
  const rows = document.querySelectorAll(".explorer-row");

  const query = (searchInput ? searchInput.value : "").trim().toLowerCase();
  const complexity = complexitySelect ? complexitySelect.value.toLowerCase() : "all";
  const topic = topicSelect ? topicSelect.value.toLowerCase() : "all";

  let visibleCount = 0;
  rows.forEach((row) => {
    const rowText = (row.textContent || "").toLowerCase();
    const rowComplexity = (row.getAttribute("data-complexity") || "").toLowerCase();
    const rowTopic = (row.getAttribute("data-topic") || "").toLowerCase();

    const matchesQuery = !query || rowText.includes(query);
    const matchesComplexity = complexity === "all" || rowComplexity === complexity;
    const matchesTopic = topic === "all" || rowTopic === topic;

    if (matchesQuery && matchesComplexity && matchesTopic) {
      row.classList.remove("hidden");
      visibleCount += 1;
    } else {
      row.classList.add("hidden");
    }
  });

  if (emptyState) {
    if (visibleCount === 0 && rows.length > 0) {
      emptyState.classList.remove("hidden");
    } else {
      emptyState.classList.add("hidden");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("search-input");
  const complexitySelect = document.getElementById("complexity-filter");
  const topicSelect = document.getElementById("topic-filter");

  const debouncedFilter = debounce(applyExplorerFilters, 200);
  if (searchInput) {
    searchInput.addEventListener("input", debouncedFilter);
  }
  if (complexitySelect) {
    complexitySelect.addEventListener("change", applyExplorerFilters);
  }
  if (topicSelect) {
    topicSelect.addEventListener("change", applyExplorerFilters);
  }
});

console.log("Explorer loaded");
