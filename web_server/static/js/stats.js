let populationChart,
  ageChart,
  deathChart,
  healthChart,
  hungerChart,
  thirstChart,
  energyChart,
  goalChart;

const HEALTH_ORDER = ["Healthy", "Hurt", "Critical"];

const dataContainer = document.getElementById("stats-data");
const ENERGY_TO_START_RESTING = parseInt(
  dataContainer.dataset.energyToStartResting
);
const ENERGY_TO_STOP_RESTING = parseInt(
  dataContainer.dataset.energyToStopResting
);
const HUNGER_TO_START_FORAGING = parseInt(
  dataContainer.dataset.hungerToStartForaging
);
const HUNGER_TO_STOP_FORAGING = parseInt(
  dataContainer.dataset.hungerToStopForaging
);
const THIRST_TO_START_DRINKING = parseInt(
  dataContainer.dataset.thirstToStartDrinking
);
const THIRST_TO_STOP_DRINKING = parseInt(
  dataContainer.dataset.thirstToStopDrinking
);

const GOAL_COLOR_MAP = {
  IDLE: "#6c757d", // Grey
  WANDER: "#6c757d", // Grey
  RESTING: "#007bff", // Blue
  SEEKING_WATER: "#0792a8", // Dark Teal
  DRINKING: "#17a2b8", // Teal
  SEEKING_FOOD: "#fd7e14", // Orange
  EATING: "#28a745", // Green
  ATTACK: "#dc3545", // Red
  FLEEING: "#ffc107", // Yellow
  SEEKING_MATE: "#e83e8c", // Pink
  BREEDING: "#e83e8c", // Pink
};

function updateBarChart(
  chartInstance,
  canvasId,
  labels,
  data,
  title,
  backgroundColors = null
) {
  if (chartInstance) {
    chartInstance.data.labels = labels;
    chartInstance.data.datasets[0].data = data;
    if (backgroundColors) {
      chartInstance.data.datasets[0].backgroundColor = backgroundColors;
    }
    chartInstance.update();
    return chartInstance;
  } else {
    const ctx = document.getElementById(canvasId).getContext("2d");
    return new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: title,
            data: data,
            backgroundColor: backgroundColors || "rgba(54, 162, 235, 0.6)",
          },
        ],
      },
      options: {
        plugins: { legend: { display: false } },
      },
    });
  }
}

function updatePieChart(
  chartInstance,
  canvasId,
  labels,
  data,
  title,
  colors = null
) {
  if (chartInstance) {
    chartInstance.data.labels = labels;
    chartInstance.data.datasets[0].data = data;
    if (colors) {
      chartInstance.data.datasets[0].backgroundColor = colors;
    }
    chartInstance.update();
    return chartInstance;
  } else {
    const ctx = document.getElementById(canvasId).getContext("2d");
    return new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            label: title,
            data: data,
            backgroundColor: colors || [
              "rgba(255, 99, 132, 0.7)",
              "rgba(54, 162, 235, 0.7)",
              "rgba(255, 206, 86, 0.7)",
              "rgba(75, 192, 192, 0.7)",
              "rgba(153, 102, 255, 0.7)",
              "rgba(255, 159, 64, 0.7)",
            ],
            hoverOffset: 4,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: "top",
          },
        },
      },
    });
  }
}

function drawDistributionChart(
  title,
  chart,
  canvasId,
  distribution,
  criticalThreshold,
  warningThreshold,
  lowIsBad
) {
  const labels = Object.keys(distribution).sort(
    (a, b) => parseInt(a) - parseInt(b)
  );
  const data = labels.map((label) => distribution[label] || 0);

  // Define colors for the states
  const okColor = "rgba(75, 192, 192, 0.6)";
  const warningColor = "rgba(255, 206, 86, 0.6)";
  const criticalColor = "rgba(255, 99, 132, 0.6)";

  // Generate a color for each bar based on its level
  const colors = labels.map((label) => {
    const lowerBound = parseInt(label.split("-")[0]);
    if (lowIsBad) {
      if (lowerBound <= criticalThreshold) {
        return criticalColor;
      } else if (lowerBound <= warningThreshold) {
        return warningColor;
      } else {
        return okColor;
      }
    } else {
      if (lowerBound >= criticalThreshold) {
        return criticalColor;
      } else if (lowerBound >= warningThreshold) {
        return warningColor;
      } else {
        return okColor;
      }
    }
  });

  return updateBarChart(chart, canvasId, labels, data, title, colors);
}

// This single function now handles both initial load and updates.
async function fetchAndDrawHistoryCharts() {
  try {
    const response = await fetch("/api/stats/history?limit=100");
    if (!response.ok) throw new Error("Failed to fetch stats history");
    const history = await response.json();

    if (history.length === 0) return;

    // --- Prepare Data ---
    const latestStat = history[history.length - 1];
    const labels = history.map((s) => s.tick);
    const herbivoreData = history.map((s) => s.herbivore_population);
    const carnivoreData = history.map((s) => s.carnivore_population);

    // --- Update or Create Population Chart ---
    if (populationChart) {
      // If chart exists, just update its data
      populationChart.data.labels = labels;
      populationChart.data.datasets[0].data = herbivoreData;
      populationChart.data.datasets[1].data = carnivoreData;
      populationChart.update();
    } else {
      // If chart doesn't exist, create it
      const popCtx = document
        .getElementById("populationChart")
        .getContext("2d");
      populationChart = new Chart(popCtx, {
        type: "line",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Herbivores",
              data: herbivoreData,
              borderColor: "rgb(153, 255, 153)",
              backgroundColor: "rgba(75, 192, 75, 0.5)",
              fill: true,
            },
            {
              label: "Carnivores",
              data: carnivoreData,
              borderColor: "rgb(255, 99, 132)",
              backgroundColor: "rgba(255, 99, 132, 0.5)",

              fill: true,
            },
          ],
        },
        options: {
          scales: {
            y: {
              beginAtZero: true,
              stacked: true,
            },
          },
        },
      });
    }

    const healthData = HEALTH_ORDER.map(
      (label) => latestStat.health_distribution[label] || 0
    );

    ageChart = updateBarChart(
      ageChart,
      "ageChart",
      Object.keys(latestStat.age_distribution),
      Object.values(latestStat.age_distribution),
      "Age Distribution"
    );
    healthChart = updateBarChart(
      healthChart,
      "healthChart",
      HEALTH_ORDER,
      healthData,
      "Health Distribution"
    );

    energyChart = drawDistributionChart(
      "Energy distribution",
      energyChart,
      "energyChart",
      latestStat.energy_distribution,
      ENERGY_TO_START_RESTING,
      ENERGY_TO_STOP_RESTING,
      true
    );
    hungerChart = drawDistributionChart(
      "Hunger distribution",
      hungerChart,
      "hungerChart",
      latestStat.hunger_distribution,
      HUNGER_TO_START_FORAGING,
      HUNGER_TO_STOP_FORAGING,
      false
    );
    thirstChart = drawDistributionChart(
      "Thirst distribution",
      thirstChart,
      "thirstChart",
      latestStat.thirst_distribution,
      THIRST_TO_START_DRINKING,
      THIRST_TO_STOP_DRINKING,
      false
    );

    const goalLabels = Object.keys(latestStat.goal_distribution).sort();
    const goalData = goalLabels.map(
      (label) => latestStat.goal_distribution[label]
    );
    const goalColors = goalLabels.map(
      (label) => GOAL_COLOR_MAP[label] || "#343a40"
    );

    goalChart = updatePieChart(
      goalChart,
      "goalChart",
      goalLabels,
      goalData,
      "Goal Distribution",
      goalColors
    );
  } catch (error) {
    console.error("Error updating charts:", error);
  }
}

async function fetchAndDrawDeathChart() {
  try {
    const response = await fetch("/api/stats/deaths");
    if (!response.ok) return;
    const deathStats = await response.json();

    const labels = Object.keys(deathStats);
    const data = Object.values(deathStats);

    deathChart = updatePieChart(
      deathChart,
      "deathChart",
      labels,
      data,
      "Cause of Death"
    );
  } catch (error) {
    console.error("Error updating death chart:", error);
  }
}

function fetchAndDrawCharts() {
  fetchAndDrawHistoryCharts();
  fetchAndDrawDeathChart();
}

// --- Initial Load and Live Update ---
window.addEventListener("load", fetchAndDrawCharts);
setInterval(fetchAndDrawHistoryCharts, 2000);
setInterval(fetchAndDrawDeathChart, 60000);
