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
const eventLogContainer = document.getElementById("event-log-container");
const imageContainer = document.getElementById("image-container");

const dataContainer = document.getElementById("simulation-data");
const DEFAULT_GRASS_FOOD = parseFloat(dataContainer.dataset.defaultGrassFood);
const MAX_ENERGY = parseInt(dataContainer.dataset.maxEnergy);
const MAX_HUNGER = parseInt(dataContainer.dataset.maxHunger);
const MAX_THIRST = parseInt(dataContainer.dataset.maxThirst);

const CRITTER_DRAW_RADIUS = 3;

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

async function fetchAndDisplayEvents() {
  if (!selectedCritter) {
    eventLogContainer.innerHTML = "";
    return;
  }
  critterId = selectedCritter.id;

  try {
    const response = await fetch(`/api/critter/${critterId}/events`);
    if (!response.ok) {
      eventLogContainer.innerHTML = "<p>Failed to load event log.</p>";
      return;
    }
    const events = await response.json();

    if (events.length === 0) {
      eventLogContainer.innerHTML = "<p>No significant events yet.</p>";
      return;
    }

    // Build the HTML for the event list
    let eventHtml = "<h3>Event Log</h3><ul>";
    for (const event of events) {
      eventHtml += `<li><span class="tick">[Tick ${event.tick}]</span> <b>${event.event}: </b>${event.description}</li>`;
    }
    eventHtml += "</ul>";

    eventLogContainer.innerHTML = eventHtml;
  } catch (error) {
    console.error("Failed to fetch event log:", error);
    eventLogContainer.innerHTML = "<p>Error loading events.</p>";
  }
}

async function updateSeasonDisplay() {
  try {
    const response = await fetch('/api/world/season');
    if (!response.ok) {
      throw new Error('${response.status}')
    }
    const data = await response.json();
    const seasonDisplay = document.getElementById('season-display');
    if (seasonDisplay) {
      seasonDisplay.textContent = data.name;
      document.body.className = `season-${data.name.toLowerCase()}`;
    }
  } catch (error) {
    console.error("Could not fetch season data: ", error);
  }
}

function updateStatsPanel() {
  console.log("Updating stats panel for:", selectedCritter);

  if (selectedCritter) {
    imageContainer.innerHTML = `
    <img src="/api/critter/${selectedCritter.id}/image.svg" alt="Critter Image" />`;
    const healthPercent =
      (selectedCritter.health / selectedCritter.max_health) * 100;
    const energyPercent = (selectedCritter.energy / MAX_ENERGY) * 100;
    const hungerPercent = (selectedCritter.hunger / MAX_HUNGER) * 100;
    const thirstPercent = (selectedCritter.thirst / MAX_THIRST) * 100;

    statsContent.innerHTML = `
            <!-- Section 1: Meters -->
            <h3>Metrics</h3>
            <div class="stat-group">
                <p><span class="stat-label">Health:</span> ${selectedCritter.health.toFixed(
      1
    )} / ${selectedCritter.max_health.toFixed(1)}</p>
                <div class="stat-meter"><div class="health-bar" style="width: ${healthPercent}%;"></div></div>
            </div>
            <div class="stat-group">
                <p><span class="stat-label">Energy:</span> ${selectedCritter.energy.toFixed(
      1
    )} / ${MAX_ENERGY}</p>
                <div class="stat-meter"><div class="energy-bar" style="width: ${energyPercent}%;"></div></div>
            </div>
            <div class="stat-group">
                <p><span class="stat-label">Hunger:</span> ${selectedCritter.hunger.toFixed(
      1
    )} / ${MAX_HUNGER}</p>
                <div class="stat-meter"><div class="hunger-bar" style="width: ${hungerPercent}%;"></div></div>
            </div>
            <div class="stat-group">
                <p><span class="stat-label">Thirst:</span> ${selectedCritter.thirst.toFixed(
      1
    )} / ${MAX_THIRST}</p>
                <div class="stat-meter"><div class="thirst-bar" style="width: ${thirstPercent}%;"></div></div>
            </div>

            <!-- Section 2: Dynamic AI Stuff -->
            <h3>AI State</h3>
            <p><span class="stat-label">Goal:</span> ${selectedCritter.ai_state
      }</p>
            <p><span class="stat-label">Last Action:</span> ${selectedCritter.last_action || "N/A"
      }</p>
            <p><span class="stat-label">Position:</span> (${selectedCritter.x
      }, ${selectedCritter.y})</p>
            <p><span class="stat-label">Velocity:</span> (${selectedCritter.vx
      }, ${selectedCritter.vy})</p>

            <!-- Section 3: Basic Info (Genetics) -->
            <h3>Genetics</h3>
            <p><span class="stat-label">ID:</span> ${selectedCritter.id}</p>
            <p><span class="stat-label">Diet:</span> ${selectedCritter.diet}</p>
            <p><span class="stat-label">Age:</span> ${selectedCritter.age}</p>
            <p><span class="stat-label">Speed:</span> ${selectedCritter.speed.toFixed(
        1
      )}</p>
            <p><span class="stat-label">Size:</span> ${selectedCritter.size.toFixed(
        1
      )}</p>
            <p><span class="stat-label">Metabolism:</span> ${selectedCritter.metabolism.toFixed(
        1
      )}</p>
            <p><span class="stat-label">Commitment:</span> ${selectedCritter.commitment.toFixed(
        1
      )}</p>
            <p><span class="stat-label">Perception:</span> ${selectedCritter.perception.toFixed(
        1
      )}</p>
        `;
  } else {
    // If no critter is selected, show the default message
    statsContent.innerHTML = `
          <p>Click on a critter to view its details.</p>
    `;
    imageContainer.innerHTML = "";
    eventLogContainer.innerHTML = "";
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

  // Are there any critters there?
  let closestCritter = null;
  let minDistance = Infinity;

  const CRITTER_CLICK_TOLERANCE = 6;

  for (const id in critterDisplayData) {
    const critter = critterDisplayData[id];

    // Use pixel space
    const critterCanvasX =
      (critter.currentX - startX) * tileWidth + tileWidth / 2;
    const critterCanvasY =
      (critter.currentY - startY) * tileHeight + tileHeight / 2;

    const distance = Math.sqrt(
      Math.pow(critterCanvasX - mouseX, 2) +
      Math.pow(critterCanvasY - mouseY, 2)
    );

    if (
      distance < CRITTER_DRAW_RADIUS + CRITTER_CLICK_TOLERANCE &&
      distance < minDistance
    ) {
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
  fetchAndDisplayEvents();
}

async function handleManualUpdate() {
  // Update the current view.
  currentView.x = xInput.value;
  currentView.y = yInput.value;
  currentView.w = widthInput.value;
  currentView.h = heightInput.value;

  const newUrl = `${window.location.pathname}?x=${currentView.x}&y=${currentView.y}&w=${currentView.w}&h=${currentView.h}`;
  history.pushState({ path: newUrl }, "", newUrl);

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

  updateSeasonDisplay();
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
      CRITTER_DRAW_RADIUS,
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
      fetchAndDisplayEvents();
    }
  }

  // Ask the browser to run this function again on the next frame
  requestAnimationFrame(animationLoop);
}

// --- Event Listeners ---
canvas.addEventListener("click", handleCanvasClick);
drawButton.addEventListener("click", handleManualUpdate);
window.addEventListener("load", () => {
  // Create a URLSearchParams object to easily read the query string.
  const urlParams = new URLSearchParams(window.location.search);

  // Check for each parameter and update the input fields if they exist.
  if (urlParams.has("x")) xInput.value = urlParams.get("x");
  if (urlParams.has("y")) yInput.value = urlParams.get("y");
  if (urlParams.has("w")) widthInput.value = urlParams.get("w");
  if (urlParams.has("h")) heightInput.value = urlParams.get("h");

  // Trigger the initial map draw. handleManualUpdate will now read
  // the values we just set from the URL.
  handleManualUpdate();
});
setInterval(handleLiveUpdate, 3000);

requestAnimationFrame(animationLoop);
