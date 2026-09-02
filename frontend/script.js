/* ============================================================
   CHAINGUARD FRONTEND
   Live dashboard integration
============================================================ */


/* ------------------------------------------------------------
   CONFIGURATION
------------------------------------------------------------ */

// LIVE BACKEND
const API_BASE = "https://chainguard-qpy6.onrender.com";

let currentShipment = "LIVE-001";

let environmentChart = null;
let integrityChart = null;


/* ------------------------------------------------------------
   DOM REFERENCES
------------------------------------------------------------ */

const shipmentInput =
    document.getElementById("shipmentInput");

const loadShipmentButton =
    document.getElementById("loadShipment");

const shipmentIdElement =
    document.getElementById("shipmentId");

const lastUpdatedElement =
    document.getElementById("lastUpdated");

const integrityScoreElement =
    document.getElementById("integrityScore");

const riskScoreElement =
    document.getElementById("riskScore");

const decisionBadge =
    document.getElementById("decisionBadge");

const decisionDescription =
    document.getElementById("decisionDescription");

const scoreRing =
    document.getElementById("scoreRing");

const deviceStatusElement =
    document.getElementById("deviceStatus");

const deviceStatusDot =
    document.getElementById("deviceStatusDot");

let previousCompletedEventCount = 0;


/* ------------------------------------------------------------
   UTILITY
------------------------------------------------------------ */

function formatNumber(value, decimals = 1) {

    if (value === null || value === undefined) {
        return "--";
    }

    return Number(value).toFixed(decimals);
}


function formatTime(timestamp) {

    if (!timestamp) {
        return "WAITING...";
    }

    const date =
        new Date(
            timestamp.replace(" ", "T") + "Z"
        );

    if (Number.isNaN(date.getTime())) {
        return timestamp;
    }

    return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
}


function showToast(message) {

    const toast =
        document.getElementById("toast");

    const toastMessage =
        document.getElementById("toastMessage");

    if (!toast || !toastMessage) {
        return;
    }

    toastMessage.textContent = message;

    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 2500);
}


/* ------------------------------------------------------------
   API
------------------------------------------------------------ */

async function fetchJSON(url) {

    const response =
        await fetch(url);

    if (!response.ok) {

        throw new Error(
            `API request failed: ${response.status}`
        );
    }

    return await response.json();
}


/* ------------------------------------------------------------
   LOAD SHIPMENT
------------------------------------------------------------ */

async function loadShipment(shipmentId) {

    currentShipment =
        shipmentId.trim();

    if (!currentShipment) {
        return;
    }

    shipmentIdElement.textContent =
        currentShipment;

    previousCompletedEventCount = 0;

    try {

        const summary =
            await fetchJSON(
                `${API_BASE}/api/shipments/${encodeURIComponent(currentShipment)}/summary`
            );

        updateDashboard(summary);

        const telemetry =
            await fetchJSON(
                `${API_BASE}/api/telemetry/${encodeURIComponent(currentShipment)}`
            );

        updateCharts(
            telemetry.telemetry || []
        );

        updateEvents(
            summary.event_history || [],
            summary.active_events || []
        );

    } catch (error) {

        console.error(error);

        showToast(
            "Unable to load shipment data"
        );

        resetDashboard();
    }
}


/* ------------------------------------------------------------
   UPDATE DASHBOARD
------------------------------------------------------------ */

function updateDashboard(summary) {

    const score =
        Number(summary.integrity_score ?? 0);

    const risk =
        Number(summary.risk_score ?? 0);

    const status =
        summary.status || "UNKNOWN";

    const telemetry =
        summary.latest_telemetry;


    /* SCORE */

    integrityScoreElement.textContent =
        Math.round(score);

    riskScoreElement.textContent =
        formatNumber(risk, 1);


    /* RING */

    const circumference = 552;

    const offset =
        circumference -
        (score / 100) * circumference;

    scoreRing.style.strokeDashoffset =
        offset;


    /* DECISION */

    updateDecision(status);


    /* LATEST TELEMETRY */

    if (telemetry) {

        updateTelemetry(telemetry);

        lastUpdatedElement.textContent =
            formatTime(telemetry.timestamp);
    }


    /* RISK BREAKDOWN */

    updateRiskBreakdown(summary);


    /* EVENT COUNT + ACTIVE EVENTS */

    const eventCount =
        Number(
            summary.total_completed_events || 0
        );

    const activeEvents =
        summary.active_events || [];

    const eventCountElement =
        document.getElementById("eventCount");

    const activeEventCountElement =
        document.getElementById(
            "activeEventCount"
        );

    if (eventCountElement) {

        eventCountElement.textContent =
            eventCount;
    }

    if (activeEventCountElement) {

        activeEventCountElement.textContent =
            `${activeEvents.length} ACTIVE`;
    }


    /* NEW EVENT NOTIFICATION */

    if (
        previousCompletedEventCount > 0 &&
        eventCount > previousCompletedEventCount
    ) {

        showToast(
            "New shipment event recorded"
        );
    }

    previousCompletedEventCount =
        eventCount;


    /* DEVICE STATUS */

    if (
        telemetry &&
        telemetry.timestamp
    ) {

        updateDeviceStatus(
            telemetry.timestamp
        );

    } else {

        updateDeviceStatus(null);
    }
}


/* ------------------------------------------------------------
   DECISION
------------------------------------------------------------ */

function updateDecision(status) {

    decisionBadge.className =
        "decision-badge";


    if (status === "ACCEPT") {

        decisionBadge.classList.add(
            "accept"
        );

        decisionBadge.textContent =
            "ACCEPT";

        decisionDescription.textContent =
            "Shipment conditions remain within the configured monitoring limits.";

        return;
    }


    if (status === "INSPECT") {

        decisionBadge.classList.add(
            "inspect"
        );

        decisionBadge.textContent =
            "INSPECT";

        decisionDescription.textContent =
            "One or more recorded conditions require shipment inspection.";

        return;
    }


    if (status === "HIGH RISK") {

        decisionBadge.classList.add(
            "high-risk"
        );

        decisionBadge.textContent =
            "HIGH RISK";

        decisionDescription.textContent =
            "Cumulative condition risk has crossed the configured high-risk threshold.";

        return;
    }


    decisionBadge.classList.add(
        "neutral"
    );

    decisionBadge.textContent =
        status;
}


/* ------------------------------------------------------------
   TELEMETRY
------------------------------------------------------------ */

function updateTelemetry(telemetry) {

    const temperature =
        Number(telemetry.temperature);

    const humidity =
        Number(telemetry.humidity);

    const acceleration =
        Number(telemetry.acceleration);

    const tamper =
        Number(telemetry.tamper_status);


    /* TEMPERATURE */

    document.getElementById(
        "temperature"
    ).textContent =
        formatNumber(
            temperature,
            1
        );

    updateSensorStatus(
        "temperatureStatus",
        "temperatureStatusDot",
        getTemperatureState(
            temperature
        )
    );


    /* HUMIDITY */

    document.getElementById(
        "humidity"
    ).textContent =
        formatNumber(
            humidity,
            1
        );

    updateSensorStatus(
        "humidityStatus",
        "humidityStatusDot",
        getHumidityState(
            humidity
        )
    );


    /* ACCELERATION */

    document.getElementById(
        "acceleration"
    ).textContent =
        formatNumber(
            acceleration,
            2
        );

    updateSensorStatus(
        "accelerationStatus",
        "accelerationStatusDot",
        getAccelerationState(
            acceleration
        )
    );


    /* TAMPER */

    const tamperStatus =
        document.getElementById(
            "tamperStatus"
        );

    const tamperText =
        document.getElementById(
            "tamperStatusText"
        );

    const tamperDot =
        document.getElementById(
            "tamperStatusDot"
        );


    if (tamper === 1) {

        tamperStatus.textContent =
            "OPEN";

        tamperText.textContent =
            "TAMPER DETECTED";

        setStatusClass(
            tamperText.parentElement,
            "danger"
        );

        if (tamperDot) {

            tamperDot.className =
                "mini-dot danger";
        }

    } else {

        tamperStatus.textContent =
            "SECURE";

        tamperText.textContent =
            "ENCLOSURE SECURE";

        setStatusClass(
            tamperText.parentElement,
            "good"
        );

        if (tamperDot) {

            tamperDot.className =
                "mini-dot good";
        }
    }
}


/* ------------------------------------------------------------
   SENSOR STATE
------------------------------------------------------------ */

function getTemperatureState(value) {

    if (
        value >= 2 &&
        value <= 8
    ) {

        return {
            text: "WITHIN RANGE",
            className: "good"
        };
    }


    if (
        (value >= 0 && value < 2) ||
        (value > 8 && value <= 10)
    ) {

        return {
            text: "MINOR EXCURSION",
            className: "warning"
        };
    }


    return {
        text: "OUT OF RANGE",
        className: "danger"
    };
}


function getHumidityState(value) {

    if (
        value >= 30 &&
        value <= 70
    ) {

        return {
            text: "WITHIN RANGE",
            className: "good"
        };
    }


    if (
        (value >= 20 && value < 30) ||
        (value > 70 && value <= 80)
    ) {

        return {
            text: "MINOR EXCURSION",
            className: "warning"
        };
    }


    return {
        text: "OUT OF RANGE",
        className: "danger"
    };
}


function getAccelerationState(value) {

    if (value <= 2.5) {

        return {
            text: "NORMAL",
            className: "good"
        };
    }


    if (value <= 6) {

        return {
            text: "ELEVATED",
            className: "warning"
        };
    }


    return {
        text: "SHOCK DETECTED",
        className: "danger"
    };
}


function updateSensorStatus(
    textId,
    dotId,
    state
) {

    const textElement =
        document.getElementById(
            textId
        );

    const dotElement =
        document.getElementById(
            dotId
        );

    if (!textElement) {
        return;
    }

    textElement.textContent =
        state.text;

    setStatusClass(
        textElement.parentElement,
        state.className
    );

    if (dotElement) {

        dotElement.className =
            `mini-dot ${state.className}`;
    }
}


function setStatusClass(
    element,
    className
) {

    if (!element) {
        return;
    }

    element.classList.remove(
        "good",
        "warning",
        "danger"
    );

    element.classList.add(
        className
    );
}


/* ------------------------------------------------------------
   RISK BREAKDOWN
------------------------------------------------------------ */

function updateRiskBreakdown(summary) {

    const events =
        summary.event_history || [];

    const activeEvents =
        summary.active_events || [];

    let temperatureRisk = 0;
    let humidityRisk = 0;
    let shockRisk = 0;
    let tamperRisk = 0;


    events.forEach(event => {

        const risk =
            Number(
                event.risk_contribution || 0
            );

        switch (
            event.event_type
        ) {

            case "temperature":

                temperatureRisk +=
                    risk;

                break;

            case "humidity":

                humidityRisk +=
                    risk;

                break;

            case "shock":

                shockRisk +=
                    risk;

                break;

            case "tamper":

                tamperRisk +=
                    risk;

                break;
        }
    });


    /*
       Active environmental/tamper events are not yet stored in
       event_history, but their risk is already included in the
       backend cumulative integrity score. Estimate their live
       contribution from the current active-event record.
    */

    activeEvents.forEach(event => {

        const severity =
            Number(
                event.severity || 0
            );

        const startedAt =
            parseBackendTimestamp(
                event.started_at
            );

        const durationSeconds =
            startedAt
                ? Math.max(
                    (
                        Date.now() -
                        startedAt.getTime()
                    ) / 1000,
                    0
                )
                : 0;

        let risk = 0;

        const weights = {
            temperature: 8,
            humidity: 3,
            tamper: 15
        };


        if (
            Object.prototype.hasOwnProperty.call(
                weights,
                event.event_type
            )
        ) {

            const durationMinutes =
                durationSeconds / 60;

            let multiplier = 1;


            if (
                durationMinutes >= 1 &&
                durationMinutes <= 5
            ) {

                multiplier = 1.25;

            } else if (
                durationMinutes > 5 &&
                durationMinutes <= 15
            ) {

                multiplier = 1.5;

            } else if (
                durationMinutes > 15 &&
                durationMinutes <= 30
            ) {

                multiplier = 2;

            } else if (
                durationMinutes > 30
            ) {

                multiplier = 2.5;
            }


            risk =
                weights[event.event_type] *
                severity *
                multiplier;
        }


        switch (
            event.event_type
        ) {

            case "temperature":

                temperatureRisk +=
                    risk;

                break;

            case "humidity":

                humidityRisk +=
                    risk;

                break;

            case "tamper":

                tamperRisk +=
                    risk;

                break;
        }
    });


    updateRiskBar(
        "tempRiskValue",
        "tempRiskBar",
        temperatureRisk
    );

    updateRiskBar(
        "humidityRiskValue",
        "humidityRiskBar",
        humidityRisk
    );

    updateRiskBar(
        "shockRiskValue",
        "shockRiskBar",
        shockRisk
    );

    updateRiskBar(
        "tamperRiskValue",
        "tamperRiskBar",
        tamperRisk
    );
}


function updateRiskBar(
    valueId,
    barId,
    value
) {

    const valueElement =
        document.getElementById(
            valueId
        );

    const barElement =
        document.getElementById(
            barId
        );

    if (valueElement) {

        valueElement.textContent =
            formatNumber(
                value,
                1
            );
    }

    if (barElement) {

        const percentage =
            Math.min(
                (value / 45) * 100,
                100
            );

        barElement.style.width =
            `${percentage}%`;
    }
}


/* ------------------------------------------------------------
   EVENTS
------------------------------------------------------------ */

function updateEvents(
    events,
    activeEvents = []
) {

    const eventList =
        document.getElementById(
            "eventList"
        );

    if (!eventList) {
        return;
    }

    const completedEvents =
        Array.isArray(events)
            ? events
            : [];

    const currentlyActive =
        Array.isArray(activeEvents)
            ? activeEvents
            : [];


    if (
        !completedEvents.length &&
        !currentlyActive.length
    ) {

        eventList.innerHTML = `
            <div class="empty-events">
                NO EVENTS RECORDED
            </div>
        `;

        return;
    }


    const activeMarkup =
        currentlyActive
            .map(event => {

                const severity =
                    Number(
                        event.severity || 0
                    );

                const eventType =
                    event.event_type ||
                    "unknown";

                const startedAt =
                    event.started_at ||
                    event.last_seen_at;

                const duration =
                    getLiveDurationSeconds(
                        startedAt
                    );

                return `
                    <div class="event-row active-event-row">

                        <span>
                            ${formatTime(startedAt)}
                        </span>

                        <span class="event-type">

                            <i class="event-marker danger pulse"></i>

                            ${getEventIcon(eventType)}
                            ${eventType.toUpperCase()}

                        </span>

                        <span>
                            <span class="severity severity-${severity}">
                                ${getSeverityLabel(severity)}
                            </span>
                        </span>

                        <span>
                            ${formatDuration(duration)}
                        </span>

                        <span class="risk-number">
                            ACTIVE
                        </span>

                    </div>
                `;

            })
            .join("");


    const sortedEvents =
        [...completedEvents]
            .reverse();


    const completedMarkup =
        sortedEvents
            .map(event => {

                const severity =
                    Number(
                        event.severity || 0
                    );

                const eventType =
                    event.event_type ||
                    "unknown";

                const duration =
                    Number(
                        event.duration_seconds ||
                        0
                    );

                const risk =
                    Number(
                        event.risk_contribution ||
                        0
                    );


                let markerClass =
                    "good";


                if (severity === 1) {

                    markerClass =
                        "warning";
                }


                if (severity === 2) {

                    markerClass =
                        "warning";
                }


                if (severity === 3) {

                    markerClass =
                        "danger";
                }


                return `
                    <div class="event-row">

                        <span>
                            ${formatTime(event.timestamp)}
                        </span>

                        <span class="event-type">

                            <i class="event-marker ${markerClass}"></i>

                            ${getEventIcon(eventType)}
                            ${eventType.toUpperCase()}

                        </span>

                        <span>
                            <span class="severity severity-${severity}">
                                ${getSeverityLabel(severity)}
                            </span>
                        </span>

                        <span>
                            ${formatDuration(duration)}
                        </span>

                        <span class="risk-number">
                            +${formatNumber(risk, 1)}
                        </span>

                    </div>
                `;

            })
            .join("");


    eventList.innerHTML =
        activeMarkup +
        completedMarkup;
}


function formatDuration(seconds) {

    if (!seconds) {
        return "INSTANT";
    }

    const minutes =
        Math.floor(
            seconds / 60
        );

    const remainingSeconds =
        Math.round(
            seconds % 60
        );


    if (minutes === 0) {

        return `${remainingSeconds}s`;
    }


    return `${minutes}m ${remainingSeconds}s`;
}


function parseBackendTimestamp(timestamp) {

    if (!timestamp) {
        return null;
    }

    const normalized =
        String(timestamp)
            .replace(" ", "T");

    const date =
        new Date(
            normalized.endsWith("Z")
                ? normalized
                : `${normalized}Z`
        );

    return Number.isNaN(
        date.getTime()
    )
        ? null
        : date;
}


function getLiveDurationSeconds(
    timestamp
) {

    const startedAt =
        parseBackendTimestamp(
            timestamp
        );

    if (!startedAt) {
        return 0;
    }

    return Math.max(
        (
            Date.now() -
            startedAt.getTime()
        ) / 1000,
        0
    );
}


function updateDeviceStatus(
    timestamp
) {

    if (
        !deviceStatusElement ||
        !deviceStatusDot
    ) {
        return;
    }


    if (!timestamp) {

        deviceStatusElement.classList.remove(
            "online",
            "offline"
        );

        deviceStatusElement.classList.add(
            "offline"
        );

        deviceStatusDot.className =
            "mini-dot offline";

        setDeviceStatusText(
            " OFFLINE"
        );

        return;
    }


    const date =
        parseBackendTimestamp(
            timestamp
        );

    if (!date) {
        return;
    }


    const ageSeconds =
        (
            Date.now() -
            date.getTime()
        ) / 1000;


    const isOnline =
        ageSeconds >= 0 &&
        ageSeconds <= 15;


    deviceStatusElement.classList.remove(
        "online",
        "offline"
    );

    deviceStatusElement.classList.add(
        isOnline
            ? "online"
            : "offline"
    );


    deviceStatusDot.className =
        `mini-dot ${
            isOnline
                ? "online"
                : "offline"
        }`;


    setDeviceStatusText(
        isOnline
            ? " ONLINE"
            : " OFFLINE"
    );
}


function setDeviceStatusText(
    text
) {

    if (!deviceStatusElement) {
        return;
    }

    const textNodes =
        Array.from(
            deviceStatusElement.childNodes
        ).filter(
            node =>
                node.nodeType ===
                Node.TEXT_NODE
        );

    if (textNodes.length) {

        textNodes[
            textNodes.length - 1
        ].textContent = text;

    } else {

        deviceStatusElement.append(
            document.createTextNode(text)
        );
    }
}
/* ------------------------------------------------------------
   CHARTS
------------------------------------------------------------ */

function updateCharts(telemetry) {

    const sorted =
        [...telemetry].reverse();


    const labels =
        sorted.map(item =>
            formatTime(item.timestamp)
        );


    const temperatures =
        sorted.map(item =>
            Number(item.temperature)
        );


    const humidities =
        sorted.map(item =>
            Number(item.humidity)
        );


    const accelerations =
        sorted.map(item =>
            Number(item.acceleration)
        );


    /* ENVIRONMENT CHART */

    const environmentCanvas =
        document.getElementById(
            "environmentChart"
        );

    if (!environmentCanvas) {
        return;
    }

    const environmentContext =
        environmentCanvas.getContext("2d");


    if (environmentChart) {
        environmentChart.destroy();
    }


    environmentChart =
        new Chart(
            environmentContext,
            {

                type: "line",

                data: {

                    labels,

                    datasets: [

                        {
                            label: "Temperature",

                            data: temperatures,

                            borderColor: "#ffb547",

                            backgroundColor:
                                "rgba(255,181,71,0.08)",

                            borderWidth: 2,

                            tension: 0.35,

                            fill: true,

                            pointRadius: 2,

                            pointHoverRadius: 5
                        },


                        {
                            label: "Humidity",

                            data: humidities,

                            borderColor: "#5bc8ff",

                            backgroundColor:
                                "rgba(91,200,255,0.05)",

                            borderWidth: 2,

                            tension: 0.35,

                            fill: false,

                            pointRadius: 2,

                            pointHoverRadius: 5,

                            yAxisID:
                                "humidityAxis"
                        }

                    ]
                },


                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    interaction: {

                        intersect: false,

                        mode: "index"
                    },


                    plugins: {

                        legend: {

                            display: false
                        },


                        tooltip: {

                            backgroundColor:
                                "#0b1012",

                            borderColor:
                                "#20282c",

                            borderWidth: 1,

                            titleFont: {

                                family: "DM Mono"
                            },

                            bodyFont: {

                                family: "DM Mono"
                            }
                        }
                    },


                    scales: {

                        x: {

                            grid: {

                                color:
                                    "rgba(255,255,255,0.035)"
                            },


                            ticks: {

                                color:
                                    "#536066",

                                font: {

                                    family:
                                        "DM Mono",

                                    size: 8
                                },

                                maxTicksLimit: 8
                            }
                        },


                        y: {

                            grid: {

                                color:
                                    "rgba(255,255,255,0.035)"
                            },


                            ticks: {

                                color:
                                    "#536066",

                                font: {

                                    family:
                                        "DM Mono",

                                    size: 8
                                }
                            }
                        },


                        humidityAxis: {

                            position: "right",


                            grid: {

                                drawOnChartArea:
                                    false
                            },


                            ticks: {

                                color:
                                    "#536066",

                                font: {

                                    family:
                                        "DM Mono",

                                    size: 8
                                }
                            }
                        }
                    }
                }
            }
        );


    /* INTEGRITY CHART */

    const integrityValues =
        calculateIntegrityTrend(
            sorted
        );


    const integrityCanvas =
        document.getElementById(
            "integrityChart"
        );

    if (!integrityCanvas) {
        return;
    }


    const integrityContext =
        integrityCanvas.getContext(
            "2d"
        );


    if (integrityChart) {
        integrityChart.destroy();
    }


    integrityChart =
        new Chart(
            integrityContext,
            {

                type: "line",

                data: {

                    labels,

                    datasets: [

                        {

                            label:
                                "Integrity",

                            data:
                                integrityValues,

                            borderColor:
                                "#b7ff3c",

                            backgroundColor:
                                "rgba(183,255,60,0.06)",

                            borderWidth: 2,

                            tension: 0.35,

                            fill: true,

                            pointRadius: 2,

                            pointHoverRadius: 5
                        }

                    ]
                },


                options: {

                    responsive: true,

                    maintainAspectRatio:
                        false,


                    plugins: {

                        legend: {

                            display: false
                        }
                    },


                    scales: {

                        x: {

                            grid: {

                                color:
                                    "rgba(255,255,255,0.035)"
                            },


                            ticks: {

                                color:
                                    "#536066",

                                font: {

                                    family:
                                        "DM Mono",

                                    size: 8
                                },

                                maxTicksLimit: 6
                            }
                        },


                        y: {

                            min: 0,

                            max: 100,


                            grid: {

                                color:
                                    "rgba(255,255,255,0.035)"
                            },


                            ticks: {

                                color:
                                    "#536066",

                                font: {

                                    family:
                                        "DM Mono",

                                    size: 8
                                }
                            }
                        }
                    }
                }
            }
        );
}


/* ------------------------------------------------------------
   INTEGRITY TREND CALCULATION
------------------------------------------------------------ */

function calculateIntegrityTrend(
    telemetry
) {

    let runningRisk = 0;


    return telemetry.map(
        item => {

            const temp =
                Number(
                    item.temperature
                );

            const humidity =
                Number(
                    item.humidity
                );

            const acceleration =
                Number(
                    item.acceleration
                );

            const tamper =
                Number(
                    item.tamper_status
                );


            let snapshotRisk = 0;


            /* Temperature */

            if (
                temp < 2 ||
                temp > 8
            ) {

                if (
                    (temp >= 0 &&
                        temp < 2) ||

                    (temp > 8 &&
                        temp <= 10)
                ) {

                    snapshotRisk += 8;

                } else {

                    snapshotRisk += 24;
                }
            }


            /* Humidity */

            if (
                humidity < 30 ||
                humidity > 70
            ) {

                if (
                    (humidity >= 20 &&
                        humidity < 30) ||

                    (humidity > 70 &&
                        humidity <= 80)
                ) {

                    snapshotRisk += 3;

                } else {

                    snapshotRisk += 9;
                }
            }


            /* Shock */

            if (
                acceleration > 6
            ) {

                snapshotRisk += 21;

            } else if (
                acceleration > 4
            ) {

                snapshotRisk += 14;

            } else if (
                acceleration > 2.5
            ) {

                snapshotRisk += 7;
            }


            /* Tamper */

            if (
                tamper === 1
            ) {

                snapshotRisk += 45;
            }


            runningRisk =
                Math.min(
                    runningRisk +
                    snapshotRisk,
                    100
                );


            return Math.max(
                100 -
                runningRisk,
                0
            );

        }
    );
}


/* ------------------------------------------------------------
   RESET
------------------------------------------------------------ */

function resetDashboard() {

    integrityScoreElement.textContent =
        "--";


    riskScoreElement.textContent =
        "--";


    decisionBadge.className =
        "decision-badge neutral";


    decisionBadge.textContent =
        "NO DATA";


    decisionDescription.textContent =
        "Unable to retrieve shipment telemetry.";


    document.getElementById(
        "temperature"
    ).textContent =
        "--";


    document.getElementById(
        "humidity"
    ).textContent =
        "--";


    document.getElementById(
        "acceleration"
    ).textContent =
        "--";


    document.getElementById(
        "tamperStatus"
    ).textContent =
        "--";


    document.getElementById(
        "lastUpdated"
    ).textContent =
        "WAITING...";


    const eventCount =
        document.getElementById(
            "eventCount"
        );

    if (eventCount) {
        eventCount.textContent = "0";
    }


    const activeEventCount =
        document.getElementById(
            "activeEventCount"
        );

    if (activeEventCount) {
        activeEventCount.textContent =
            "0 ACTIVE";
    }


    updateDeviceStatus(null);


    const eventList =
        document.getElementById(
            "eventList"
        );

    if (eventList) {

        eventList.innerHTML = `
            <div class="empty-events">
                NO EVENTS RECORDED
            </div>
        `;
    }
}


/* ------------------------------------------------------------
   SEVERITY / EVENT HELPERS
------------------------------------------------------------ */

function getSeverityLabel(
    severity
) {

    switch (
        Number(severity)
    ) {

        case 3:

            return "CRITICAL";


        case 2:

            return "HIGH";


        case 1:

            return "MODERATE";


        default:

            return "NORMAL";
    }
}


function getEventIcon(
    eventType
) {

    switch (
        eventType
    ) {

        case "temperature":

            return "🌡";


        case "humidity":

            return "💧";


        case "shock":

            return "⚡";


        case "tamper":

            return "🔓";


        default:

            return "⚠";
    }
}


/* ------------------------------------------------------------
   AUTO REFRESH
------------------------------------------------------------ */

async function refreshCurrentShipment() {

    try {

        const summary =
            await fetchJSON(
                `${API_BASE}/api/shipments/${encodeURIComponent(currentShipment)}/summary`
            );


        updateDashboard(
            summary
        );


        const telemetry =
            await fetchJSON(
                `${API_BASE}/api/telemetry/${encodeURIComponent(currentShipment)}`
            );


        updateCharts(
            telemetry.telemetry || []
        );


        /*
           IMPORTANT:
           Pass both completed and active events.
           Otherwise active events disappear after refresh.
        */

        updateEvents(
            summary.event_history || [],
            summary.active_events || []
        );


    } catch (error) {

        console.error(
            "Auto-refresh failed:",
            error
        );
    }
}


/* ------------------------------------------------------------
   EVENTS
------------------------------------------------------------ */

loadShipmentButton.addEventListener(
    "click",
    () => {

        loadShipment(
            shipmentInput.value
        );
    }
);


shipmentInput.addEventListener(
    "keydown",
    event => {

        if (event.key === "Enter") {

            loadShipment(
                shipmentInput.value
            );
        }
    }
);


/* ------------------------------------------------------------
   INITIAL LOAD
------------------------------------------------------------ */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadShipment(
            currentShipment
        );


        setInterval(
            refreshCurrentShipment,
            5000
        );
    }
);
