document.addEventListener("DOMContentLoaded", function () {
  const ctxReward = document.getElementById("rewardChart").getContext("2d");
  const ctxConcordance = document
    .getElementById("concordanceChart")
    .getContext("2d");

  function createMultiLineChart(ctx, title, yAxisLabel) {
    return new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Herbivore",
            data: [],
            borderColor: "rgba(75, 192, 192, 1)", // Teal
            borderWidth: 1,
            fill: false,
            tension: 0.1,
          },
          {
            label: "Carnivore",
            data: [],
            borderColor: "rgba(255, 99, 132, 1)", // Red
            borderWidth: 1,
            fill: false,
            tension: 0.1,
          },
        ],
      },
      options: {
        scales: {
          x: { title: { display: true, text: "Tick" } },
          y: { title: { display: true, text: yAxisLabel } },
        },
      },
    });
  }

  const rewardChart = createMultiLineChart(
    ctxReward,
    "Average Reward",
    "Reward",
  );
  const concordanceChart = createMultiLineChart(
    ctxConcordance,
    "Concordance",
    "Concordance (%)",
  );

  function updateCharts() {
    fetch("/api/training_stats")
      .then((response) => response.json())
      .then((data) => {
        const labels = data.map((s) => s.tick);

        function updateChartData(chart, herbivoreData, carnivoreData) {
          chart.data.labels = labels;
          chart.data.datasets[0].data = herbivoreData;
          chart.data.datasets[1].data = carnivoreData;
          chart.update();
        }

        updateChartData(
          rewardChart,
          data.map((s) => s.avg_reward_herbivore),
          data.map((s) => s.avg_reward_carnivore),
        );
        updateChartData(
          concordanceChart,
          data.map((s) => s.avg_concordance_herbivore * 100), // As percentage
          data.map((s) => s.avg_concordance_carnivore * 100), // As percentage
        );

        const latestStats = data[data.length - 1]; // Get the most recent data point
        document.getElementById("herb-epsilon").textContent =
          latestStats.herbivore_epsilon.toFixed(4);
        document.getElementById("carn-epsilon").textContent =
          latestStats.carnivore_epsilon.toFixed(4);
      });
  }

  setInterval(updateCharts, 30000);
  updateCharts();
});
