// --- DOM Elements ---
const canvas = document.getElementById("world-canvas");
const ctx = canvas.getContext("2d");
const xInput = document.getElementById("x-coord");
const yInput = document.getElementById("y-coord");
const widthInput = document.getElementById("width");
const heightInput = document.getElementById("height");
const drawButton = document.getElementById("draw-btn");
const statsPanel = document.getElementById("stats-panel");
const statsContent = document.getElementById("stats-content");

const dataContainer = document.getElementById("simulation-data");
const DEFAULT_GRASS_FOOD = parseFloat(dataContainer.dataset.defaultGrassFood);
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
const MAX_ENERGY = parseInt(dataContainer.dataset.maxEnergy);

let currentTerrainData = null;
let currentView = {
  x: parseInt(xInput.value),
  y: parseInt(yInput.value),
  w: parseInt(widthInput.value),
  h: parseInt(heightInput.value),
};
let critterDisplayData = {};
let selectedCritter = null;

// --- Color Map (must match TerrainType enum names) ---
const colorMap = {
  WATER: "#4287f5",
  GRASS: "#34a12d",
  DIRT: "#855a38",
  MOUNTAIN: "#a1a2a3",
};

// Takes a hex colour and percentage (-1.0 to 1.0) and
// returns a new hex color from dark to light.
function shadeColor(color, percent) {
  let R = parseInt(color.substring(1, 3), 16);
  let G = parseInt(color.substring(3, 5), 16);
  let B = parseInt(color.substring(5, 7), 16);

  R = parseInt(R * (1.0 + percent));
  G = parseInt(G * (1.0 + percent));
  B = parseInt(B * (1.0 + percent));

  // CLAMP
  R = R < 255 ? R : 255;
  G = G < 255 ? G : 255;
  B = B < 255 ? B : 255;

  R = R > 0 ? R : 0;
  G = G > 0 ? G : 0;
  B = B > 0 ? B : 0;

  const RR = R.toString(16).length == 1 ? "0" + R.toString(16) : R.toString(16);
  const GG = G.toString(16).length == 1 ? "0" + G.toString(16) : G.toString(16);
  const BB = B.toString(16).length == 1 ? "0" + B.toString(16) : B.toString(16);

  return "#" + RR + GG + BB;
}

function interpolateColor(color1, color2, factor) {
  let color_1_rgb = [
    parseInt(color1.substring(1, 3), 16),
    parseInt(color1.substring(3, 5), 16),
    parseInt(color1.substring(5, 7), 16),
  ];
  let color_2_rgb = [
    parseInt(color2.substring(1, 3), 16),
    parseInt(color2.substring(3, 5), 16),
    parseInt(color2.substring(5, 7), 16),
  ];

  let final_color_rgb = [0, 0, 0];

  for (let i = 0; i < 3; i++) {
    final_color_rgb[i] = Math.round(
      color_1_rgb[i] * (1 - factor) + color_2_rgb[i] * factor
    );
  }

  return (
    "#" + final_color_rgb.map((c) => c.toString(16).padStart(2, "0")).join("")
  );
}

async function fetchTerrain(view) {
  const apiUrl = `/api/world/terrain?x=${view.x}&y=${view.y}&w=${view.w}&h=${view.h}`;

  const response = await fetch(apiUrl);
  if (!response.ok) throw new Error("Failed to fetch terrain");
  currentTerrainData = await response.json();
}

async function fetchCritters(view) {
  const apiUrl = `/api/world/critters?x=${view.x}&y=${view.y}&w=${view.w}&h=${view.h}`;
  const response = await fetch(apiUrl);
  if (!response.ok) throw new Error("Failed to fetch critters");
  return await response.json();
}

function drawTerrain(view) {
  if (!currentTerrainData) return;
  const tiles = currentTerrainData.tiles;
  const tileWidth = canvas.width / view.w;
  const tileHeight = canvas.height / view.h;

  for (let i = 0; i < tiles.length; i++) {
    const tile = tiles[i];
    const x = i % view.w;
    const y = Math.floor(i / view.w);

    let baseColor;
    if (tile.terrain === "GRASS") {
      const foodPercent = tile.food_available / DEFAULT_GRASS_FOOD;
      baseColor = interpolateColor(colorMap.DIRT, colorMap.GRASS, foodPercent);
    } else {
      baseColor = colorMap[tile.terrain] || "#000";
    }

    const finalColor = shadeColor(baseColor, tile.height * 0.4);
    ctx.fillStyle = finalColor;
    ctx.fillRect(x * tileWidth, y * tileHeight, tileWidth, tileHeight);
  }
}

function updateStatsPanel() {
  if (selectedCritter) {
    const healthPercent =
      (selectedCritter.health / selectedCritter.max_health) * 100;
    const energyPercent = (selectedCritter.energy / MAX_ENERGY) * 100;

    // Determine status text based on AI thresholds
    const energyStatus =
      selectedCritter.energy < ENERGY_TO_START_RESTING
        ? '<span class="status-text">(Tired)</span>'
        : selectedCritter.energy < ENERGY_TO_STOP_RESTING
        ? '<span class="status-text">(Resting)</span>'
        : "";
    const hungerStatus =
      selectedCritter.hunger >= HUNGER_TO_START_FORAGING
        ? '<span class="status-text">(Hungry)</span>'
        : selectedCritter.hunger >= HUNGER_TO_STOP_FORAGING
        ? '<span class="status-text">(Foraging)</span>'
        : "";
    const thirstStatus =
      selectedCritter.thirst >= THIRST_TO_START_DRINKING
        ? '<span class="status-text">(Thirsty)</span>'
        : selectedCritter.thirst >= THIRST_TO_STOP_DRINKING
        ? '<span class="status-text">(Drinking)</span>'
        : "";

    // If a critter is selected, build the HTML with its stats
    statsPanel.innerHTML = `
      <h2>Critter Stats</h2>
      <p><span class="stat-label">ID:</span> ${selectedCritter.id}</p>
      <p><span class="stat-label">Diet:</span> ${selectedCritter.diet}</p>
      <p><span class="stat-label">Age:</span> ${selectedCritter.age}</p>
      <p><span class="stat-label">Speed:</span> ${selectedCritter.speed.toFixed(
        1
      )}</p>
      <p><span class="stat-label">Size:</span> ${selectedCritter.size.toFixed(
        1
      )}</p>

      <div>
        <p><span class="stat-label">Health:</span> ${selectedCritter.health.toFixed(
          1
        )} / ${selectedCritter.max_health.toFixed(1)}</p>
        <div class="stat-meter"><div class="health-bar" style="width: ${healthPercent}%;"></div></div>
      </div>
            
      <div>
        <p><span class="stat-label">Energy:</span> ${selectedCritter.energy.toFixed(
          1
        )} / ${MAX_ENERGY} ${energyStatus}</p>
        <div class="stat-meter"><div class="energy-bar" style="width: ${energyPercent}%;"></div></div>
      </div>

      <p><span class="stat-label">Hunger:</span> ${selectedCritter.hunger.toFixed(
        1
      )} ${hungerStatus}</p>
      <p><span class="stat-label">Thirst:</span> ${selectedCritter.thirst.toFixed(
        1
      )} ${thirstStatus}</p>
    `;
  } else {
    // If no critter is selected, show the default message
    statsPanel.innerHTML = `
            <h2>Critter Stats</h2>
            <p>Click on a critter to view its details.</p>
        `;
  }
}

function handleCanvasClick(event) {
  if (!currentTerrainData || !currentView) return;

  const rect = canvas.getBoundingClientRect();
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;

  const tileWidth = canvas.width / currentView.w;
  const tileHeight = canvas.height / currentView.h;
  const startX = currentView.x - currentView.w / 2;
  const startY = currentView.y - currentView.h / 2;

  const clickedWorldX = Math.floor(startX + mouseX / tileWidth);
  const clickedWorldY = Math.floor(startY + mouseY / tileHeight);

  // Are there any critters there?
  let closestCritter = null;
  let minDistance = Infinity;
  const CLICK_RADIUS = 1.5;

  for (const id in critterDisplayData) {
    const critter = critterDisplayData[id];

    const distance = Math.sqrt(
      Math.pow(critter.currentX - clickedWorldX, 2) +
        Math.pow(critter.currentY - clickedWorldY, 2)
    );

    if (distance < CLICK_RADIUS && distance < minDistance) {
      closestCritter = critter.critter;
      minDistance = distance;
    }
  }

  if (closestCritter) {
    console.log("clicked on ", closestCritter);
    selectedCritter = closestCritter;
  } else {
    console.log("didn't hit a critter");
    selectedCritter = null;
  }

  updateStatsPanel();
}

async function handleManualUpdate() {
  // Update the current view.
  currentView.x = xInput.value;
  currentView.y = yInput.value;
  currentView.w = widthInput.value;
  currentView.h = heightInput.value;

  try {
    await fetchTerrain(currentView);
    drawTerrain(currentView);

    const critterData = await fetchCritters(currentView);

    // Clear data on a manual update
    critterDisplayData = {};
    for (const critter of critterData.critters) {
      critterDisplayData[critter.id] = {
        currentX: critter.x,
        currentY: critter.y,
        targetX: critter.x,
        targetY: critter.y,
        critter: critter,
      };
    }
  } catch (error) {
    console.error(error);
  }
}

async function handleLiveUpdate() {
  if (!currentTerrainData) return; // Don't run if the map isn't loaded

  try {
    // Use cached current view.
    const critterData = await fetchCritters(currentView);

    // Remove any critter that isn't on the live list.
    const liveCritterIds = new Set(critterData.critters.map((c) => c.id));
    for (const id in critterDisplayData) {
      if (!liveCritterIds.has(parseInt(id))) {
        delete critterDisplayData[id];
      }
    }

    for (const critter of critterData.critters) {
      if (critterDisplayData[critter.id]) {
        critterDisplayData[critter.id].targetX = critter.x;
        critterDisplayData[critter.id].targetY = critter.y;
        critterDisplayData[critter.id].critter = critter;
      } else {
        // New critter
        critterDisplayData[critter.id] = {
          currentX: critter.x,
          currentY: critter.y,
          targetX: critter.x,
          targetY: critter.y,
          critter: critter,
        };
      }
    }
  } catch (error) {
    console.error(error);
  }
}

function animationLoop() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawTerrain(currentView);

  const tileWidth = canvas.width / currentView.w;
  const tileHeight = canvas.height / currentView.h;
  const startX = currentView.x - currentView.w / 2;
  const startY = currentView.y - currentView.h / 2;

  for (const id in critterDisplayData) {
    const critter = critterDisplayData[id];

    // Move the current position a fraction of the way towards the target
    // This creates the smooth animation.
    critter.currentX += (critter.targetX - critter.currentX) * 0.1;
    critter.currentY += (critter.targetY - critter.currentY) * 0.1;

    // Set color based on diet
    if (critter.critter.diet === "HERBIVORE") {
      ctx.fillStyle = "cyan";
    } else if (critter.critter.diet === "CARNIVORE") {
      ctx.fillStyle = "red";
    } else {
      ctx.fillStyle = "grey";
    }

    // Draw the critter at its current, interpolated position
    const canvasX = (critter.currentX - startX) * tileWidth;
    const canvasY = (critter.currentY - startY) * tileHeight;

    ctx.beginPath();
    ctx.arc(
      canvasX + tileWidth / 2,
      canvasY + tileHeight / 2,
      tileWidth / 2.0,
      0,
      2 * Math.PI
    );
    ctx.fill();
  }

  // Update live stats
  if (selectedCritter) {
    const latestData = critterDisplayData[selectedCritter.id];
    if (latestData) {
      selectedCritter = latestData.critter;
      updateStatsPanel();
    }
  }

  // Ask the browser to run this function again on the next frame
  requestAnimationFrame(animationLoop);
}

// --- Event Listeners ---
canvas.addEventListener("click", handleCanvasClick);
drawButton.addEventListener("click", handleManualUpdate);
window.addEventListener("load", handleManualUpdate);
setInterval(handleLiveUpdate, 3000);

requestAnimationFrame(animationLoop);
