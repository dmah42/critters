// --- Read Constants from HTML data attributes ---
const dataContainer = document.getElementById("stats-data");
// These are the exact constants you provided
const ENERGY_TO_START_RESTING = parseInt(
  dataContainer.dataset.energyToStartResting
);
const CRITICAL_ENERGY = parseInt(dataContainer.dataset.criticalEnergy);
const HUNGER_TO_START_FORAGING = parseInt(
  dataContainer.dataset.hungerToStartForaging
);
const CRITICAL_HUNGER = parseInt(dataContainer.dataset.criticalHunger);
const THIRST_TO_START_DRINKING = parseInt(
  dataContainer.dataset.thirstToStartDrinking
);
const CRITICAL_THIRST = parseInt(dataContainer.dataset.criticalThirst);

// --- NEW: A central place for our color palettes ---
const COLORS = {
  green: {
    good: "rgba(75, 192, 75, 0.7)",
    warn: "rgba(139, 213, 139, 0.7)",
    crit: "rgba(183, 233, 183, 0.7)",
  },
  red: {
    good: "rgba(255, 99, 132, 0.7)",
    warn: "rgba(255, 159, 162, 0.7)",
    crit: "rgba(255, 205, 210, 0.7)",
  },
  blue: {
    good: "rgba(54, 162, 235, 0.7)",
    warn: "rgba(137, 196, 244, 0.7)",
    crit: "rgba(187, 222, 251, 0.7)",
  },
  orange: {
    good: "rgba(255, 159, 64, 0.7)",
    warn: "rgba(255, 204, 128, 0.7)",
    crit: "rgba(255, 224, 178, 0.7)",
  },
};

// --- Chart Objects ---
let populationChart,
  ageChart,
  healthChart,
  hungerChart,
  thirstChart,
  energyChart,
  deathChart,
  goalChart;

// --- Color Maps ---
const GOAL_COLOR_MAP = {
  IDLE: "#6c757d",
  RESTING: "#007bff",
  SEEKING_WATER: "#078298",
  DRINKING: "#17a2b8",
  SEEKING_FOOD: "#fd7e14",
  EATING: "#28a745",
  ATTACK: "#dc3545",
  FLEEING: "#ffc107",
  SEEKING_MATE: "#d82e7c",
  BREEDING: "#e83e8c",
};

// --- Helper Functions ---
function updateBarChart(chartInstance, canvasId, labels, datasets) {
  if (chartInstance) {
    chartInstance.data.labels = labels;
    chartInstance.data.datasets = datasets;
    chartInstance.update();
    return chartInstance;
  } else {
    const ctx = document.getElementById(canvasId).getContext("2d");
    return new Chart(ctx, {
      type: "bar",
      data: { labels: labels, datasets: datasets },
      options: { scales: { y: { beginAtZero: true } } },
    });
  }
}

function updatePieChart(
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
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            label: title,
            data: data,
            backgroundColor: backgroundColors || [
              "#ff6384",
              "#36a2eb",
              "#ffce56",
              "#4bc0c0",
              "#9966ff",
              "#ff9f40",
            ],
            hoverOffset: 4,
          },
        ],
      },
      options: { responsive: true, plugins: { legend: { position: "top" } } },
    });
  }
}

// --- Main Fetching and Drawing Logic ---
async function fetchAndDrawHistoryCharts() {
  try {
    const response = await fetch("/api/stats/history?limit=200");
    if (!response.ok) throw new Error("Failed to fetch stats history");
    const history = await response.json();
    if (history.length === 0) return;

    const latestStat = history[history.length - 1];

    // --- Population Chart (Stacked Area) ---
    if (populationChart) {
      populationChart.data.labels = history.map((s) => s.tick);
      populationChart.data.datasets[0].data = history.map(
        (s) => s.herbivore_population
      );
      populationChart.data.datasets[1].data = history.map(
        (s) => s.carnivore_population
      );
      populationChart.update();
    } else {
      const popCtx = document
        .getElementById("populationChart")
        .getContext("2d");
      populationChart = new Chart(popCtx, {
        type: "line",
        data: {
          labels: history.map((s) => s.tick),
          datasets: [
            {
              label: "Herbivores",
              data: history.map((s) => s.herbivore_population),
              borderColor: "rgb(75, 192, 75)",
              backgroundColor: "rgba(75, 192, 75, 0.5)",
              fill: true,
            },
            {
              label: "Carnivores",
              data: history.map((s) => s.carnivore_population),
              borderColor: "rgb(255, 99, 132)",
              backgroundColor: "rgba(255, 99, 132, 0.5)",
              fill: true,
            },
          ],
        },
        options: { scales: { y: { beginAtZero: true, stacked: true } } },
      });
    }

    // --- Health Chart (Grouped Bar) ---
    const healthLabels = ["Healthy", "Hurt", "Critical"];
    const healthDatasets = [
      {
        label: "Herbivores",
        data: healthLabels.map(
          (l) => latestStat.herbivore_health_distribution[l] || 0
        ),
        backgroundColor: "rgba(75, 192, 75, 0.6)",
      },
      {
        label: "Carnivores",
        data: healthLabels.map(
          (l) => latestStat.carnivore_health_distribution[l] || 0
        ),
        backgroundColor: "rgba(255, 99, 132, 0.6)",
      },
    ];
    healthChart = updateBarChart(
      healthChart,
      "healthChart",
      healthLabels,
      healthDatasets
    );

    // --- Energy Chart (Grouped Bar with Threshold Coloring) ---
    const allEnergyKeys = [
      ...Object.keys(latestStat.herbivore_energy_distribution),
      ...Object.keys(latestStat.carnivore_energy_distribution),
    ];
    const energyLabels = [...new Set(allEnergyKeys)]
      .map((k) => parseInt(k))
      .sort((a, b) => a - b);
    const energyDatasets = [
      {
        label: "Herbivores",
        data: energyLabels.map(
          (l) => latestStat.herbivore_energy_distribution[l] || 0
        ),
        backgroundColor: energyLabels.map((label) => {
          if (label <= CRITICAL_ENERGY) return COLORS.green.crit;
          if (label <= ENERGY_TO_START_RESTING) return COLORS.green.warn;
          return COLORS.green.good;
        }),
      },
      {
        label: "Carnivores",
        data: energyLabels.map(
          (l) => latestStat.carnivore_energy_distribution[l] || 0
        ),
        backgroundColor: energyLabels.map((label) => {
          if (label <= CRITICAL_ENERGY) return COLORS.red.crit;
          if (label <= ENERGY_TO_START_RESTING) return COLORS.red.warn;
          return COLORS.red.good;
        }),
      },
    ];
    energyChart = updateBarChart(
      energyChart,
      "energyChart",
      energyLabels,
      energyDatasets
    );

    // --- Hunger Chart (Grouped Bar with Threshold Coloring) ---
    const allHungerKeys = [
      ...Object.keys(latestStat.herbivore_hunger_distribution),
      ...Object.keys(latestStat.carnivore_hunger_distribution),
    ];
    const hungerLabels = [...new Set(allHungerKeys)]
      .map((k) => parseInt(k))
      .sort((a, b) => a - b);
    const hungerDatasets = [
      {
        label: "Herbivores",
        data: hungerLabels.map(
          (l) => latestStat.herbivore_hunger_distribution[l] || 0
        ),
        backgroundColor: hungerLabels.map((label) => {
          if (label >= CRITICAL_HUNGER) return COLORS.green.crit;
          if (label >= HUNGER_TO_START_FORAGING) return COLORS.green.warn;
          return COLORS.green.good;
        }),
      },
      {
        label: "Carnivores",
        data: hungerLabels.map(
          (l) => latestStat.carnivore_hunger_distribution[l] || 0
        ),
        backgroundColor: hungerLabels.map((label) => {
          if (label >= CRITICAL_HUNGER) return COLORS.red.crit;
          if (label >= HUNGER_TO_START_FORAGING) return COLORS.red.warn;
          return COLORS.red.good;
        }),
      },
    ];
    hungerChart = updateBarChart(
      hungerChart,
      "hungerChart",
      hungerLabels,
      hungerDatasets
    );

    // --- Thirst Chart (Grouped Bar with Threshold Coloring) ---
    const allThirstKeys = [
      ...Object.keys(latestStat.herbivore_thirst_distribution),
      ...Object.keys(latestStat.carnivore_thirst_distribution),
    ];
    const thirstLabels = [...new Set(allThirstKeys)]
      .map((k) => parseInt(k))
      .sort((a, b) => a - b);
    const thirstDatasets = [
      {
        label: "Herbivores",
        data: thirstLabels.map(
          (l) => latestStat.herbivore_thirst_distribution[l] || 0
        ),
        backgroundColor: thirstLabels.map((label) => {
          if (label >= CRITICAL_THIRST) return COLORS.green.crit;
          if (label >= THIRST_TO_START_DRINKING) return COLORS.green.warn;
          return COLORS.green.good;
        }),
      },
      {
        label: "Carnivores",
        data: thirstLabels.map(
          (l) => latestStat.carnivore_thirst_distribution[l] || 0
        ),
        backgroundColor: thirstLabels.map((label) => {
          if (label >= CRITICAL_THIRST) return COLORS.red.crit;
          if (label >= THIRST_TO_START_DRINKING) return COLORS.red.warn;
          return COLORS.red.good;
        }),
      },
    ];
    thirstChart = updateBarChart(
      thirstChart,
      "thirstChart",
      thirstLabels,
      thirstDatasets
    );

    // --- Age Chart (Grouped Bar) ---
    const allAgeKeys = [
      ...Object.keys(latestStat.herbivore_age_distribution),
      ...Object.keys(latestStat.carnivore_age_distribution),
    ];
    const ageLabels = [...new Set(allAgeKeys)]
      .map((k) => parseInt(k))
      .sort((a, b) => a - b);
    const ageDatasets = [
      {
        label: "Herbivores",
        data: ageLabels.map(
          (l) => latestStat.herbivore_age_distribution[l] || 0
        ),
        backgroundColor: "rgba(75, 192, 75, 0.6)",
      },
      {
        label: "Carnivores",
        data: ageLabels.map(
          (l) => latestStat.carnivore_age_distribution[l] || 0
        ),
        backgroundColor: "rgba(255, 99, 132, 0.6)",
      },
    ];
    ageChart = updateBarChart(ageChart, "ageChart", ageLabels, ageDatasets);

    // --- Goal Chart (Pie) ---
    const goalDistributionData = latestStat.goal_distribution;
    const goalLabels = Object.keys(goalDistributionData).sort();
    const goalData = goalLabels.map((label) => goalDistributionData[label]);
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
    console.error("Error updating history charts:", error);
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

// --- Initial Load and Timers ---
function initialLoad() {
  fetchAndDrawHistoryCharts();
  fetchAndDrawDeathChart();
}

window.addEventListener("load", initialLoad);
setInterval(fetchAndDrawHistoryCharts, 5000);
setInterval(fetchAndDrawDeathChart, 30000);
