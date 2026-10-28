let selectedFailedOrderId = null;
let selectedFailedOrderCode = null;

let locationWatcherId = null;
let gpsHeartbeatTimer = null;
let shipperSessionHeartbeatTimer = null;

let currentDriverPosition = null;
let lastSentPosition = null;
let lastSentAt = 0;
let gpsSendInFlight = false;

let shipperSessionConflictHandled = false;

const deliveryMapStates = new Map();

const SESSION_CODES = new Set([
  "SESSION_INVALID",
  "SESSION_CONFLICT",
  "SHIPPER_LOCKED",
]);

// Khởi tạo giao diện shipper và đăng ký sự kiện khi trang tải xong.
document.addEventListener("DOMContentLoaded", async () => {
  setupSidebarNavigation();

  setupSectionLinks();

  setupWorkButton();

  setupOrderActions();

  setupFailedDeliveryModal();

  buildFilteredOrderSections();

  updateActiveOrderCount();

  setupDeliveryMaps();

  /*
   * Kiểm tra phiên trước khi bật GPS.
   *
   * Nếu đây là máy cũ đã bị máy khác đăng nhập đè,
   * máy này sẽ không bắt đầu watchPosition().
   */

  const sessionIsValid = await setupSessionGuard();

  if (sessionIsValid) {
    setupGPS();
  }

  setupVisibilityGuards();
});

// Bắt đầu kiểm tra định kỳ để phát hiện phiên shipper bị thay thế.
async function setupSessionGuard() {
  // Chỉ bật GPS sau khi backend xác nhận token của trình duyệt còn là token mới nhất.
  const sessionIsValid = await checkActiveShipperSession();

  if (!sessionIsValid || shipperSessionConflictHandled) {
    return false;
  }

  shipperSessionHeartbeatTimer = window.setInterval(
    checkActiveShipperSession,
    4000,
  );

  return true;
}

// Gọi máy chủ để xác nhận phiên đăng nhập shipper còn hiệu lực.
async function checkActiveShipperSession() {
  if (shipperSessionConflictHandled) {
    return false;
  }

  try {
    // Máy chủ so token trong cookie với ActiveSessionToken; kiểm tra lại mỗi 4 giây.
    const response = await fetch("/shipper/session-status", {
      method: "GET",

      cache: "no-store",

      credentials: "same-origin",
    });

    const data = await readJsonResponse(response);

    if (isSessionTerminationResponse(response, data)) {
      handleShipperSessionTermination(data);

      return false;
    }

    if (!response.ok || !data.success) {
      console.warn(
        data.message || "Không thể kiểm tra phiên đăng nhập Shipper.",
      );

      /*
       * Không logout chỉ vì server lỗi 500
       * hoặc mạng hơi dở chứng.
       */

      return true;
    }

    return true;
  } catch (error) {
    /*
     * Mất Internet tạm thời
     * không đồng nghĩa thiết bị khác login.
     */

    console.warn("Session heartbeat error:", error);

    return true;
  }
}

// Nhận diện phản hồi cho biết phiên đăng nhập đã hết hạn hoặc bị thay thế.
function isSessionTerminationResponse(response, data) {
  if (response.status !== 401) {
    return false;
  }

  /*
   * Nếu backend trả 401 nhưng body JSON lỗi,
   * vẫn coi phiên đã hết hiệu lực.
   */

  if (!data || typeof data !== "object") {
    return true;
  }

  return !data.code || SESSION_CODES.has(data.code);
}

// Xử lý phản hồi từ API cần đăng nhập và kết thúc phiên khi cần.
function handleProtectedResponse(response, data) {
  if (!isSessionTerminationResponse(response, data)) {
    return false;
  }

  handleShipperSessionTermination(data);

  return true;
}

// Thông báo phiên bị kết thúc, dừng tác vụ nền và đưa shipper về đăng nhập.
function handleShipperSessionTermination(data = {}) {
  if (shipperSessionConflictHandled) {
    return;
  }

  // Chặn xử lý lặp nếu nhiều request cùng nhận được phiên đã hết hiệu lực.
  shipperSessionConflictHandled = true;

  /*
   * Dừng mọi nguồn có thể tiếp tục gửi GPS
   * hoặc cập nhật giao diện.
   */

  // Dừng GPS/heartbeat trước khi rời trang để máy cũ không tiếp tục gửi dữ liệu.
  stopGPS();

  stopSessionHeartbeat();

  stopMapAnimations();

  const code = data.code || "SESSION_INVALID";

  const message =
    data.message ||
    (code === "SESSION_CONFLICT"
      ? "Tài khoản Shipper đã được đăng nhập trên thiết bị khác."
      : code === "SHIPPER_LOCKED"
        ? "Tài khoản Shipper đã bị khóa."
        : "Phiên đăng nhập Shipper không còn hợp lệ.");

  let reason = "session_invalid";

  if (code === "SESSION_CONFLICT") {
    reason = "session_conflict";
  } else if (code === "SHIPPER_LOCKED") {
    reason = "account_locked";
  }

  window.alert(
    message + "\n\nThiết bị này sẽ dừng gửi GPS và quay về trang đăng nhập.",
  );

  window.location.replace(`/login?reason=${encodeURIComponent(reason)}`);
}

// Tiếp tục kiểm tra phiên khi tab được hiện lại.
function setupVisibilityGuards() {
  /*
   * Trình duyệt thường throttle setInterval khi tab nằm nền.
   * Khi người dùng quay lại tab, kiểm tra session ngay.
   */

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && !shipperSessionConflictHandled) {
      checkActiveShipperSession();

      refreshDeliveryMapSizes();
    }
  });

  /*
   * Xử lý trường hợp browser phục hồi trang từ BFCache.
   */

  window.addEventListener("pageshow", () => {
    if (!shipperSessionConflictHandled) {
      checkActiveShipperSession();
    }
  });
}

// Dừng bộ hẹn giờ kiểm tra phiên shipper.
function stopSessionHeartbeat() {
  if (shipperSessionHeartbeatTimer) {
    window.clearInterval(shipperSessionHeartbeatTimer);

    shipperSessionHeartbeatTimer = null;
  }
}

// Khởi tạo điều hướng giữa các mục trong trang shipper.
function setupSidebarNavigation() {
  document.querySelectorAll(".menu-item[data-target]").forEach((item) => {
    item.addEventListener("click", () => {
      openSection(item.dataset.target);
    });
  });
}

// Đăng ký thao tác mở mục tương ứng khi shipper chọn menu.
function setupSectionLinks() {
  document.querySelectorAll("[data-open-section]").forEach((button) => {
    button.addEventListener("click", () => {
      openSection(button.dataset.openSection);
    });
  });
}

// Hiển thị mục được chọn và cập nhật trạng thái menu.
function openSection(sectionId) {
  if (!sectionId) {
    return;
  }

  document.querySelectorAll(".menu-item[data-target]").forEach((item) => {
    item.classList.toggle("active", item.dataset.target === sectionId);
  });

  document.querySelectorAll(".content-section").forEach((section) => {
    section.classList.toggle("active", section.id === sectionId);
  });

  /*
   * Leaflet cần invalidateSize sau khi map
   * được chuyển từ display:none sang visible.
   */

  window.setTimeout(() => {
    setupDeliveryMaps();

    refreshDeliveryMapSizes();
  }, 100);

  window.scrollTo({
    top: 0,

    behavior: "smooth",
  });
}

// Phân đơn vào danh sách đang xử lý, đã giao và giao thất bại.
function buildFilteredOrderSections() {
  const sourceCards = [...document.querySelectorAll("#overview .order-card")];

  const activeContainer = document.querySelector(
    '[data-filter-section="active"]',
  );

  const completedContainer = document.querySelector(
    '[data-filter-section="completed"]',
  );

  const failedContainer = document.querySelector(
    '[data-filter-section="failed"]',
  );

  if (activeContainer) {
    activeContainer.innerHTML = "";
  }

  if (completedContainer) {
    completedContainer.innerHTML = "";
  }

  if (failedContainer) {
    failedContainer.innerHTML = "";
  }

  let activeCount = 0;

  let completedCount = 0;

  let failedCount = 0;

  sourceCards.forEach((card) => {
    const status = (card.dataset.orderStatus || "").trim();

    if (isActiveOrderStatus(status)) {
      activeCount += 1;

      appendCardClone(activeContainer, card);
    }

    if (status === "Hoàn thành") {
      completedCount += 1;

      appendCardClone(completedContainer, card);
    }

    if (isFailedOrderStatus(status)) {
      failedCount += 1;

      appendCardClone(failedContainer, card);
    }
  });

  if (activeContainer && activeCount === 0) {
    activeContainer.innerHTML = createEmptyState(
      "🛵",

      "Không có đơn đang xử lý",

      "Bạn hiện không có đơn nào cần giao.",
    );
  }

  if (completedContainer && completedCount === 0) {
    completedContainer.innerHTML = createEmptyState(
      "✓",

      "Chưa có đơn hoàn thành",

      "Các đơn giao thành công sẽ xuất hiện tại đây.",
    );
  }

  if (failedContainer && failedCount === 0) {
    failedContainer.innerHTML = createEmptyState(
      "📦",

      "Không có đơn giao thất bại",

      "Hiện chưa có đơn nào được ghi nhận là không giao được.",
    );
  }
}

// Sao chép thẻ đơn vào danh sách đích.
function appendCardClone(container, card) {
  if (!container) {
    return;
  }

  container.appendChild(card.cloneNode(true));
}

// Tạo thông báo khi danh sách đơn không có dữ liệu.
function createEmptyState(icon, title, description) {
  return `

        <div class="empty-state">

            <div class="empty-icon">
                ${icon}
            </div>

            <h3>
                ${title}
            </h3>

            <p>
                ${description}
            </p>

        </div>

    `;
}

// Kiểm tra đơn có đang ở trạng thái cần shipper xử lý hay không.
function isActiveOrderStatus(status) {
  return ["Đã giao shipper", "Đang chuẩn bị", "Đang giao"].includes(status);
}

// Kiểm tra đơn có trạng thái giao thất bại hoặc đã hủy hay không.
function isFailedOrderStatus(status) {
  return ["Không giao được", "Đã hủy"].includes(status);
}

// Cập nhật số đơn đang xử lý trên menu.
function updateActiveOrderCount() {
  const count = [...document.querySelectorAll("#overview .order-card")].filter(
    (card) => {
      return isActiveOrderStatus((card.dataset.orderStatus || "").trim());
    },
  ).length;

  const menuCount = document.getElementById("activeOrderCount");

  if (menuCount) {
    menuCount.textContent = String(count);
  }

  document.querySelectorAll(".active-orders-total").forEach((element) => {
    element.textContent = String(count);
  });
}

// Gắn thao tác bật hoặc tắt trạng thái nhận đơn.
function setupWorkButton() {
  const button = document.getElementById("toggleWorkBtn");

  if (!button) {
    return;
  }

  button.addEventListener("click", async () => {
    if (button.disabled || shipperSessionConflictHandled) {
      return;
    }

    const oldText = button.textContent;

    button.disabled = true;

    button.textContent = "Đang xử lý...";

    try {
      const response = await fetch("/shipper/toggle-work", {
        method: "POST",

        credentials: "same-origin",
      });

      const data = await readJsonResponse(response);

      /*
       * Nếu đây là thiết bị cũ,
       * không hiển thị lỗi chung.
       * Dừng session ngay.
       */

      if (handleProtectedResponse(response, data)) {
        return;
      }

      if (!response.ok || !data.success) {
        throw new Error(data.message || "Không thể thay đổi trạng thái ca.");
      }

      window.location.reload();
    } catch (error) {
      console.error("Toggle work error:", error);

      if (!shipperSessionConflictHandled) {
        window.alert(error.message || "Không thể kết nối tới máy chủ.");

        button.disabled = false;

        button.textContent = oldText;
      }
    }
  });
}

// Gắn sự kiện cho nút cập nhật trạng thái và báo giao thất bại.
function setupOrderActions() {
  document.addEventListener("click", async (event) => {
    const statusButton = event.target.closest(".status-btn");

    if (statusButton) {
      event.preventDefault();

      await updateOrderStatus(statusButton);

      return;
    }

    const failedButton = event.target.closest(".failed-order-btn");

    if (failedButton) {
      event.preventDefault();

      openFailedDeliveryModal(failedButton);
    }
  });
}

// Gửi trạng thái mới của đơn lên máy chủ và cập nhật giao diện.
async function updateOrderStatus(button) {
  if (shipperSessionConflictHandled) {
    return;
  }

  const orderId = button.dataset.id;

  const newStatus = button.dataset.status;

  if (!orderId || !newStatus) {
    return;
  }

  const confirmations = {
    "Đang chuẩn bị": "Xác nhận bạn đã nhận món cho đơn này?",

    "Đang giao": "Xác nhận bắt đầu giao đơn hàng?",

    "Hoàn thành": "Xác nhận khách đã nhận hàng và bạn đã thu tiền?",
  };

  const message = confirmations[newStatus];

  if (message && !window.confirm(message)) {
    return;
  }

  const oldContent = button.innerHTML;

  button.disabled = true;

  button.innerHTML = "Đang cập nhật...";

  try {
    const response = await fetch(
      `/shipper/update/${encodeURIComponent(orderId)}`,

      {
        method: "POST",

        credentials: "same-origin",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          status: newStatus,
        }),
      },
    );

    const data = await readJsonResponse(response);

    if (handleProtectedResponse(response, data)) {
      return;
    }

    if (!response.ok || !data.success) {
      throw new Error(data.message || "Không thể cập nhật trạng thái đơn.");
    }

    window.location.reload();
  } catch (error) {
    console.error("Update order error:", error);

    if (!shipperSessionConflictHandled) {
      window.alert(error.message || "Không thể kết nối tới máy chủ.");

      button.disabled = false;

      button.innerHTML = oldContent;
    }
  }
}

// Đăng ký các nút mở, đóng và xác nhận hộp thoại giao thất bại.
function setupFailedDeliveryModal() {
  const modal = document.getElementById("failedDeliveryModal");

  const closeButton = document.getElementById("closeFailedModal");

  const cancelButton = document.getElementById("cancelFailedModal");

  const confirmButton = document.getElementById("confirmFailedDelivery");

  closeButton?.addEventListener("click", closeFailedDeliveryModal);

  cancelButton?.addEventListener("click", closeFailedDeliveryModal);

  confirmButton?.addEventListener("click", submitFailedDelivery);

  modal?.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeFailedDeliveryModal();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeFailedDeliveryModal();
    }
  });
}

// Mở hộp thoại và nạp thông tin đơn cần báo giao thất bại.
function openFailedDeliveryModal(button) {
  if (shipperSessionConflictHandled) {
    return;
  }

  const modal = document.getElementById("failedDeliveryModal");

  if (!modal) {
    return;
  }

  selectedFailedOrderId = button.dataset.id || null;

  selectedFailedOrderCode = button.dataset.code || null;

  const code = document.getElementById("failedOrderCode");

  if (code) {
    code.textContent = `Đơn #${
      selectedFailedOrderCode || selectedFailedOrderId || ""
    }`;
  }

  const reason = document.getElementById("failedReason");

  const note = document.getElementById("failedNote");

  if (reason) {
    reason.value = "";
  }

  if (note) {
    note.value = "";
  }

  modal.classList.add("show");

  document.body.style.overflow = "hidden";
}

// Đóng hộp thoại giao thất bại và xóa dữ liệu tạm.
function closeFailedDeliveryModal() {
  const modal = document.getElementById("failedDeliveryModal");

  if (!modal) {
    return;
  }

  modal.classList.remove("show");

  document.body.style.overflow = "";

  selectedFailedOrderId = null;

  selectedFailedOrderCode = null;
}

// Gửi lý do giao thất bại lên máy chủ rồi làm mới danh sách.
async function submitFailedDelivery() {
  if (!selectedFailedOrderId || shipperSessionConflictHandled) {
    return;
  }

  const reasonElement = document.getElementById("failedReason");

  const noteElement = document.getElementById("failedNote");

  const confirmButton = document.getElementById("confirmFailedDelivery");

  const reason = reasonElement?.value.trim() || "";

  const note = noteElement?.value.trim() || "";

  if (!reason) {
    window.alert("Bạn cần chọn lý do không giao được.");

    reasonElement?.focus();

    return;
  }

  if (!window.confirm("Xác nhận đơn hàng này không thể giao?")) {
    return;
  }

  if (confirmButton) {
    confirmButton.disabled = true;

    confirmButton.textContent = "Đang lưu...";
  }

  try {
    const response = await fetch(
      `/shipper/cancel/${encodeURIComponent(selectedFailedOrderId)}`,

      {
        method: "POST",

        credentials: "same-origin",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          reason,

          note,
        }),
      },
    );

    const data = await readJsonResponse(response);

    if (handleProtectedResponse(response, data)) {
      return;
    }

    if (!response.ok || !data.success) {
      throw new Error(data.message || "Không thể ghi nhận đơn giao thất bại.");
    }

    window.location.reload();
  } catch (error) {
    console.error("Failed delivery error:", error);

    if (!shipperSessionConflictHandled) {
      window.alert(error.message || "Không thể kết nối tới máy chủ.");

      if (confirmButton) {
        confirmButton.disabled = false;

        confirmButton.textContent = "Xác nhận không giao được";
      }
    }
  }
}

// Khởi tạo bản đồ và tuyến đường cho các đơn đang giao.
function setupDeliveryMaps() {
  if (typeof L === "undefined") {
    return;
  }

  document
    .querySelectorAll(".content-section.active .shipper-map-panel")
    .forEach((panel) => {
      const mapElement = panel.querySelector(".shipper-route-map");

      if (!mapElement || mapElement.dataset.mapReady === "1") {
        return;
      }

      const destinationLat = Number(panel.dataset.destinationLat);

      const destinationLng = Number(panel.dataset.destinationLng);

      if (
        !Number.isFinite(destinationLat) ||
        !Number.isFinite(destinationLng)
      ) {
        return;
      }

      const map = L.map(mapElement, {
        zoomControl: true,
      }).setView(
        [destinationLat, destinationLng],

        15,
      );

      L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",

        {
          maxZoom: 19,

          attribution: "&copy; OpenStreetMap",
        },
      ).addTo(map);

      const customerIcon = L.divIcon({
        className: "shipper-customer-marker-wrap",

        html: '<div class="shipper-customer-marker">📍</div>',

        iconSize: [42, 48],

        iconAnchor: [21, 44],
      });

      L.marker(
        [destinationLat, destinationLng],

        {
          icon: customerIcon,
        },
      )
        .addTo(map)
        .bindPopup(
          `<strong>Khách hàng</strong><br>${escapeMapHTML(
            panel.dataset.address || "Điểm giao hàng",
          )}`,
        );

      const state = {
        panel,

        mapElement,

        map,

        destination: {
          lat: destinationLat,

          lng: destinationLng,
        },

        driverMarker: null,

        routeLayer: null,

        routePoints: [],

        animationFrame: null,

        lastPosition: null,

        lastRoutePosition: null,

        lastRouteAt: 0,

        routeLoading: false,

        hasFittedBounds: false,
      };

      deliveryMapStates.set(mapElement, state);

      mapElement.dataset.mapReady = "1";

      if (currentDriverPosition) {
        updateDeliveryMapPosition(
          state,

          currentDriverPosition,

          true,
        );
      }

      window.setTimeout(() => {
        map.invalidateSize();
      }, 120);
    });
}

// Cập nhật kích thước bản đồ khi bố cục hoặc cửa sổ thay đổi.
function refreshDeliveryMapSizes() {
  deliveryMapStates.forEach((state) => {
    if (state.mapElement.offsetParent !== null) {
      state.map.invalidateSize();
    }
  });
}

// Tạo biểu tượng xe shipper theo hướng di chuyển.
function createDriverIcon(bearing = 0) {
  return L.divIcon({
    className: "shipper-live-marker-wrap",

    html: `

            <div class="shipper-live-marker">

                <div
                    class="shipper-bike-body"
                    style="transform: rotate(${bearing}deg)"
                >

                    🛵

                </div>

            </div>

            `,

    iconSize: [54, 54],

    iconAnchor: [27, 27],
  });
}

// Cập nhật vị trí shipper, điểm đích và tuyến đường.
function updateDeliveryMapPosition(state, position, forceRoute = false) {
  if (!state || !position || shipperSessionConflictHandled) {
    return;
  }

  const snapped = state.routePoints.length
    ? snapPositionToRoute(state.routePoints, position)
    : position;

  const bearing = state.lastPosition
    ? calculateBearing(
        state.lastPosition.lat,

        state.lastPosition.lng,

        snapped.lat,

        snapped.lng,
      )
    : 0;

  if (!state.driverMarker) {
    state.driverMarker = L.marker(
      [snapped.lat, snapped.lng],

      {
        icon: createDriverIcon(bearing),

        zIndexOffset: 1000,
      },
    )
      .addTo(state.map)
      .bindPopup("<strong>Vị trí của bạn</strong><br>GPS đang hoạt động");
  } else {
    animateDeliveryMarker(
      state,

      snapped,

      bearing,
    );
  }

  state.lastPosition = {
    lat: snapped.lat,

    lng: snapped.lng,
  };

  const gpsText = state.panel.querySelector(".shipper-map-gps-text");

  const liveStatus = state.panel.querySelector(".shipper-map-live-status");

  if (gpsText) {
    const accuracy = Number(position.accuracy);

    gpsText.textContent = Number.isFinite(accuracy)
      ? `GPS trực tiếp • sai số khoảng ${Math.round(accuracy)} m`
      : "GPS thiết bị đang được cập nhật trực tiếp.";
  }

  if (liveStatus) {
    liveStatus.textContent = "Trực tiếp";

    liveStatus.classList.add("is-live");
  }

  if (!state.hasFittedBounds) {
    state.map.fitBounds(
      L.latLngBounds([
        [snapped.lat, snapped.lng],

        [state.destination.lat, state.destination.lng],
      ]),

      {
        padding: [45, 45],

        maxZoom: 16,
      },
    );

    state.hasFittedBounds = true;
  }

  refreshDeliveryRoute(
    state,

    position,

    forceRoute,
  );
}

// Di chuyển biểu tượng shipper tới tọa độ GPS mới.
function animateDeliveryMarker(state, targetPosition, bearing) {
  if (!state.driverMarker) {
    return;
  }

  if (state.animationFrame) {
    cancelAnimationFrame(state.animationFrame);
  }

  const current = state.driverMarker.getLatLng();

  const start = {
    lat: current.lat,

    lng: current.lng,
  };

  const duration = 1800;

  const startedAt = performance.now();

  function frame(now) {
    if (shipperSessionConflictHandled) {
      state.animationFrame = null;

      return;
    }

    const progress = Math.min(
      (now - startedAt) / duration,

      1,
    );

    const eased =
      progress < 0.5
        ? 2 * progress * progress
        : 1 -
          Math.pow(
            -2 * progress + 2,

            2,
          ) /
            2;

    const lat = start.lat + (targetPosition.lat - start.lat) * eased;

    const lng = start.lng + (targetPosition.lng - start.lng) * eased;

    state.driverMarker.setLatLng([lat, lng]);

    const bike = state.driverMarker
      .getElement()
      ?.querySelector(".shipper-bike-body");

    if (bike) {
      bike.style.transform = `rotate(${bearing}deg)`;
    }

    if (progress < 1) {
      state.animationFrame = requestAnimationFrame(frame);
    } else {
      state.animationFrame = null;
    }
  }

  state.animationFrame = requestAnimationFrame(frame);
}

// Lấy hoặc làm mới tuyến đường giao hàng.
async function refreshDeliveryRoute(state, position, force = false) {
  if (state.routeLoading || shipperSessionConflictHandled) {
    return;
  }

  const now = Date.now();

  const moved = state.lastRoutePosition
    ? distanceBetweenMeters(
        state.lastRoutePosition.lat,

        state.lastRoutePosition.lng,

        position.lat,

        position.lng,
      )
    : Number.POSITIVE_INFINITY;

  /*
   * Không gọi OSRM liên tục.
   * Chỉ refresh nếu:
   * - force
   * - shipper đã đi >= 25 m
   * - hoặc route đã cũ >= 15 giây
   */

  if (!force && moved < 25 && now - state.lastRouteAt < 15000) {
    return;
  }

  state.routeLoading = true;

  try {
    const url =
      "https://router.project-osrm.org/route/v1/driving/" +
      `${encodeURIComponent(position.lng)},${encodeURIComponent(position.lat)};` +
      `${encodeURIComponent(state.destination.lng)},${encodeURIComponent(state.destination.lat)}` +
      "?overview=full&geometries=geojson&steps=false";

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error("Routing service unavailable");
    }

    const data = await response.json();

    const route = data.routes?.[0];

    if (!route) {
      throw new Error("Không có tuyến đường.");
    }

    const points = route.geometry.coordinates.map(([lng, lat]) => {
      return [lat, lng];
    });

    state.routePoints = points;

    if (state.routeLayer) {
      state.routeLayer.setLatLngs(points);
    } else {
      state.routeLayer = L.polyline(points, {
        color: "#7a0c1e",

        weight: 5,

        opacity: 0.85,
      }).addTo(state.map);
    }

    updateRouteMetrics(
      state,

      route.distance,

      route.duration,
    );

    state.lastRoutePosition = {
      lat: position.lat,

      lng: position.lng,
    };

    state.lastRouteAt = now;
  } catch (error) {
    console.warn("Không lấy được tuyến đường OSRM:", error);

    /*
     * OSRM lỗi thì fallback đường thẳng.
     * GPS vẫn hoạt động.
     */

    const distance = distanceBetweenMeters(
      position.lat,

      position.lng,

      state.destination.lat,

      state.destination.lng,
    );

    const fallback = [
      [position.lat, position.lng],

      [state.destination.lat, state.destination.lng],
    ];

    state.routePoints = fallback;

    if (state.routeLayer) {
      state.routeLayer.setLatLngs(fallback);
    } else {
      state.routeLayer = L.polyline(fallback, {
        color: "#7a0c1e",

        weight: 4,

        opacity: 0.55,

        dashArray: "8 10",
      }).addTo(state.map);
    }

    updateRouteMetrics(
      state,

      distance,

      null,
    );
  } finally {
    state.routeLoading = false;
  }
}

// Hiển thị quãng đường và thời gian dự kiến còn lại.
function updateRouteMetrics(state, distanceMeters, durationSeconds) {
  const distanceElement = state.panel.querySelector(".shipper-map-distance");

  const etaElement = state.panel.querySelector(".shipper-map-eta");

  if (distanceElement) {
    distanceElement.textContent = formatDistance(distanceMeters);
  }

  if (etaElement) {
    etaElement.textContent = Number.isFinite(Number(durationSeconds))
      ? formatDuration(durationSeconds)
      : "Đang tính";
  }
}

// Xin quyền vị trí và bắt đầu theo dõi GPS của shipper.
function setupGPS() {
  if (shipperSessionConflictHandled) {
    return;
  }

  const isWorking = document.body.dataset.working === "1";

  if (!isWorking) {
    updateAllMapGPSStatus(
      "Đang nghỉ ca",

      false,
    );

    return;
  }

  if (!navigator.geolocation) {
    updateAllMapGPSStatus(
      "Thiết bị không hỗ trợ GPS",

      false,
    );

    return;
  }

  /*
   * Tránh vô tình setup nhiều watchPosition
   * trên cùng trang.
   */

  if (locationWatcherId !== null) {
    return;
  }

  locationWatcherId = navigator.geolocation.watchPosition(
    handleDriverPosition,

    handleLocationError,

    {
      enableHighAccuracy: true,

      maximumAge: 1500,

      timeout: 12000,
    },
  );

  /*
   * Heartbeat GPS.
   *
   * Kể cả shipper đứng yên vẫn gửi lại GPS
   * để phía khách biết vị trí còn "fresh".
   */

  gpsHeartbeatTimer = window.setInterval(() => {
    if (currentDriverPosition && !shipperSessionConflictHandled) {
      sendLocation(
        currentDriverPosition,

        true,
      );
    }
  }, 10000);
}

// Dừng theo dõi GPS và gửi trạng thái ngừng hoạt động nếu cần.
function stopGPS() {
  if (locationWatcherId !== null && navigator.geolocation) {
    navigator.geolocation.clearWatch(locationWatcherId);

    locationWatcherId = null;
  }

  if (gpsHeartbeatTimer) {
    window.clearInterval(gpsHeartbeatTimer);

    gpsHeartbeatTimer = null;
  }

  gpsSendInFlight = false;
}

// Xử lý tọa độ GPS mới từ trình duyệt.
function handleDriverPosition(position) {
  if (shipperSessionConflictHandled) {
    return;
  }

  const latitude = Number(position.coords.latitude);

  const longitude = Number(position.coords.longitude);

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    return;
  }

  currentDriverPosition = {
    lat: latitude,

    lng: longitude,

    accuracy: Number(position.coords.accuracy) || null,

    timestamp: position.timestamp || Date.now(),
  };

  /*
   * Update map của chính shipper ngay lập tức.
   */

  setupDeliveryMaps();

  deliveryMapStates.forEach((state) => {
    updateDeliveryMapPosition(
      state,

      currentDriverPosition,
    );
  });

  const now = Date.now();

  const moved = lastSentPosition
    ? distanceBetweenMeters(
        lastSentPosition.lat,

        lastSentPosition.lng,

        latitude,

        longitude,
      )
    : Number.POSITIVE_INFINITY;

  /*
   * Gửi server nếu:
   * - đã di chuyển >= 5 m
   * - hoặc GPS gần nhất đã >= 5 giây
   */

  if (moved >= 5 || now - lastSentAt >= 5000) {
    sendLocation(
      currentDriverPosition,

      false,
    );
  }
}

// Gửi tọa độ hiện tại của shipper lên máy chủ.
async function sendLocation(position, force = false) {
  if (!position || gpsSendInFlight || shipperSessionConflictHandled) {
    return;
  }

  const now = Date.now();

  if (!force && now - lastSentAt < 2000) {
    return;
  }

  gpsSendInFlight = true;

  try {
    const response = await fetch("/shipper/location", {
      method: "POST",

      credentials: "same-origin",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        latitude: position.lat,

        longitude: position.lng,
      }),
    });

    const data = await readJsonResponse(response);

    /*
     * Đây là phần quan trọng mà file cũ thiếu.
     *
     * Nếu máy B đã login,
     * máy A gửi GPS sẽ nhận 401.
     *
     * Máy A lập tức:
     * - stop watchPosition
     * - stop heartbeat
     * - stop map animation
     * - redirect login
     */

    if (handleProtectedResponse(response, data)) {
      return;
    }

    if (!response.ok || !data.success) {
      console.warn(data.message || "Server từ chối cập nhật GPS.");

      return;
    }

    lastSentAt = Date.now();

    lastSentPosition = {
      lat: position.lat,

      lng: position.lng,
    };
  } catch (error) {
    console.error("GPS request error:", error);
  } finally {
    gpsSendInFlight = false;
  }
}

// Xử lý lỗi khi trình duyệt không lấy được vị trí GPS.
function handleLocationError(error) {
  if (shipperSessionConflictHandled) {
    return;
  }

  let message = "Không lấy được GPS";

  switch (error.code) {
    case error.PERMISSION_DENIED:
      message = "Chưa cấp quyền vị trí";

      break;

    case error.POSITION_UNAVAILABLE:
      message = "Không xác định được vị trí";

      break;

    case error.TIMEOUT:
      message = "GPS phản hồi quá chậm";

      break;

    default:
      message = error.message || message;
  }

  updateAllMapGPSStatus(
    message,

    false,
  );

  console.warn("Lỗi GPS:", message);
}

// Cập nhật trạng thái GPS trên tất cả bản đồ giao hàng.
function updateAllMapGPSStatus(text, isLive) {
  document.querySelectorAll(".shipper-map-gps-text").forEach((element) => {
    element.textContent = text;
  });

  document.querySelectorAll(".shipper-map-live-status").forEach((element) => {
    element.textContent = text;

    element.classList.toggle(
      "is-live",

      Boolean(isLive),
    );
  });
}

// Dừng các hiệu ứng di chuyển trên bản đồ.
function stopMapAnimations() {
  deliveryMapStates.forEach((state) => {
    if (state.animationFrame) {
      cancelAnimationFrame(state.animationFrame);

      state.animationFrame = null;
    }
  });
}

// Tính khoảng cách giữa hai tọa độ địa lý theo mét.
function distanceBetweenMeters(lat1, lng1, lat2, lng2) {
  const earthRadius = 6371000;

  const toRadians = Math.PI / 180;

  const dLat = (lat2 - lat1) * toRadians;

  const dLng = (lng2 - lng1) * toRadians;

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * toRadians) *
      Math.cos(lat2 * toRadians) *
      Math.sin(dLng / 2) ** 2;

  return (
    earthRadius *
    2 *
    Math.atan2(
      Math.sqrt(a),

      Math.sqrt(1 - a),
    )
  );
}

// Tính hướng di chuyển giữa hai tọa độ.
function calculateBearing(lat1, lng1, lat2, lng2) {
  const toRadians = Math.PI / 180;

  const toDegrees = 180 / Math.PI;

  const phi1 = lat1 * toRadians;

  const phi2 = lat2 * toRadians;

  const deltaLambda = (lng2 - lng1) * toRadians;

  const y = Math.sin(deltaLambda) * Math.cos(phi2);

  const x =
    Math.cos(phi1) * Math.sin(phi2) -
    Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);

  return (Math.atan2(y, x) * toDegrees + 360) % 360;
}

// Chiếu vị trí GPS lên tuyến đường để xe bám sát đường đi.
function snapPositionToRoute(points, position) {
  if (!Array.isArray(points) || points.length === 0) {
    return position;
  }

  let bestPoint = null;

  let bestDistance = Number.POSITIVE_INFINITY;

  for (const point of points) {
    const distance = distanceBetweenMeters(
      position.lat,

      position.lng,

      point[0],

      point[1],
    );

    if (distance < bestDistance) {
      bestDistance = distance;

      bestPoint = point;
    }
  }

  /*
   * Nếu GPS lệch route quá 80m,
   * giữ GPS thật thay vì ép xe sang đường sai.
   */

  if (!bestPoint || bestDistance > 80) {
    return position;
  }

  return {
    lat: bestPoint[0],

    lng: bestPoint[1],
  };
}

// Định dạng quãng đường để hiển thị dễ đọc.
function formatDistance(distanceMeters) {
  const meters = Number(distanceMeters);

  if (!Number.isFinite(meters)) {
    return "-- km";
  }

  if (meters < 1000) {
    return `${Math.max(Math.round(meters), 0)} m`;
  }

  return `${(meters / 1000).toLocaleString("vi-VN", {
    minimumFractionDigits: 1,

    maximumFractionDigits: 1,
  })} km`;
}

// Định dạng thời gian dự kiến thành phút hoặc giờ.
function formatDuration(durationSeconds) {
  const seconds = Number(durationSeconds);

  if (!Number.isFinite(seconds)) {
    return "-- phút";
  }

  const minutes = Math.max(
    Math.ceil(seconds / 60),

    1,
  );

  if (minutes < 60) {
    return `${minutes} phút`;
  }

  const hours = Math.floor(minutes / 60);

  const remaining = minutes % 60;

  return remaining ? `${hours} giờ ${remaining} phút` : `${hours} giờ`;
}

// Mã hóa nội dung trước khi chèn vào HTML bản đồ.
function escapeMapHTML(value) {
  const div = document.createElement("div");

  div.textContent = String(value || "");

  return div.innerHTML;
}

// Đọc JSON an toàn và xử lý phản hồi API không hợp lệ.
async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch (error) {
    console.error("Response không phải JSON:", error);

    return {
      success: false,

      message: "Server trả về dữ liệu không hợp lệ.",
    };
  }
}

// Dọn GPS, bộ hẹn giờ và hiệu ứng bản đồ khi rời trang.
window.addEventListener("beforeunload", () => {
  stopGPS();

  stopSessionHeartbeat();

  stopMapAnimations();
});
