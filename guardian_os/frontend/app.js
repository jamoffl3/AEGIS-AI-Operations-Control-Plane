/*

 * AEGIS — Last-Mile Operations Control Plane

 *

 * Frontend responsibilities:

 * 1. Interactive sidebar navigation

 * 2. AWS assessment execution

 * 3. Human approval gate

 * 4. Intervention execution

 * 5. Prediction vs actual evaluation

 * 6. Dynamic operational control-loop state

 *

 * Backend:

 * API Gateway → Lambda → FastAPI → DynamoDB

 */



const API_BASE_URL =

  "https://ohfqclcdwg.execute-api.ap-south-1.amazonaws.com";
  



const ASSESS_EVENT_ENDPOINT =

  `${API_BASE_URL}/api/v1/events/assess`;



const HEALTH_ENDPOINT =

  `${API_BASE_URL}/api/v1/health`;



const DEMO_REQUEST = {

  event: {

    event_id: "EVT-UI-0001",

    event_type: "STATION_CAPACITY_SHOCK",

    station_id: "CHN-017",

    city: "Chennai",

    region: "Tamil Nadu",

    severity: "HIGH",

    description: "Synthetic station capacity disruption",

    capacity_change_percent: -20,

    metadata: {

      simulation: true,

      source: "AEGIS_COMMAND_CENTER"

    }

  },



  station: {

    station_id: "CHN-017",

    city: "Chennai",

    region: "Tamil Nadu",

    capacity: 8000,

    current_load: 8200,

    active_routes: 384

  }

};



let currentAssessmentId = null;

let currentAssessment = null;

let approvalInProgress = false;

let assessmentInProgress = false;

let navigationObserver = null;



const $ = id =>

  document.getElementById(id);



const setText = (

  id,

  value

) => {

  const el = $(id);



  if (el) {

    el.textContent = value;

  }

};



const number = (

  value,

  decimals = 2

) => {

  const n = Number(value);



  return Number.isFinite(n)

    ? n.toFixed(decimals)

    : "—";

};



const percent = value => {

  const n = Number(value);



  return Number.isFinite(n)

    ? `${n.toFixed(2)}%`

    : "—";

};



const formatNumber = (

  value,

  decimals = 0

) => {

  const n = Number(value);



  return Number.isFinite(n)

    ? n.toLocaleString(

        "en-IN",

        {

          minimumFractionDigits:

            decimals,

          maximumFractionDigits:

            decimals

        }

      )

    : "—";

};



const approveEndpoint = id =>

  `${API_BASE_URL}/api/v1/assessments/${encodeURIComponent(

    id

  )}/approve`;



const assessmentEndpoint = id =>

  `${API_BASE_URL}/api/v1/assessments/${encodeURIComponent(

    id

  )}`;



const normalizeLabel = value =>

  String(value || "")

    .replace(/\s+/g, " ")

    .trim()

    .replace(/\s+\d+$/, "")

    .replace(/^[^\p{L}\p{N}]+/u, "")

    .trim();



const normalizeStrategy = strategy =>

  String(strategy || "")

    .replaceAll("_", " ")

    .replace(/\s+/g, " ")

    .trim()

    .toLowerCase();





/* =========================================================

   SYSTEM STATE

   \========================================================= */



const SYSTEM_STATE = {

  READY: "READY",

  ANALYZING: "ANALYZING",

  AWAITING_APPROVAL: "AWAITING APPROVAL",

  EXECUTING: "EXECUTING",

  EXECUTED: "EXECUTED",

  ERROR: "ERROR"

};



function setSystemStatus(

  status

) {

  setText(

    "controlStatus",

    status

  );



  updateSystemIndicators(

    status

  );

}



function updateSystemIndicators(

  status = SYSTEM_STATE.READY

) {

  /*

   * The existing HTML does not require new IDs.

   * We locate the status indicators conservatively.

   */



  const candidates = [

    ...document.querySelectorAll(

      ".status-item, .system-status, .status-indicator, .header-status, .top-status"

    )

  ];



  if (!candidates.length) {

    return;

  }



  candidates.forEach(

    item => {

      const text =

        normalizeLabel(

          item.textContent

        ).toUpperCase();



      if (

        text.includes("API")

      ) {

        item.dataset.aegisState =

          "READY";

      }



      if (

        text.includes(

          "CONTROL PLANE"

        )

      ) {

        item.dataset.aegisState =

          status;

      }



      if (

        text.includes("AWS")

      ) {

        item.dataset.aegisState =

          "READY";

      }

    }

  );

}



function updateOperationalIndicators(

  state

) {

  const status =

    String(state || "")

      .toUpperCase();



  const statusMap = {

    READY: {

      label: "READY",

      api: "READY",

      control: "READY",

      aws: "READY"

    },



    ANALYZING: {

      label: "ANALYZING",

      api: "ONLINE",

      control: "ANALYZING",

      aws: "CONNECTED"

    },



    "AWAITING APPROVAL": {

      label: "AWAITING APPROVAL",

      api: "ONLINE",

      control: "AWAITING APPROVAL",

      aws: "CONNECTED"

    },



    EXECUTING: {

      label: "EXECUTING",

      api: "ONLINE",

      control: "EXECUTING",

      aws: "CONNECTED"

    },



    EXECUTED: {

      label: "EXECUTED",

      api: "ONLINE",

      control: "EXECUTED",

      aws: "CONNECTED"

    },



    ERROR: {

      label: "ERROR",

      api: "ERROR",

      control: "ERROR",

      aws: "CHECK"

    }

  };



  const mapped =

    statusMap[status] ||

    statusMap.READY;



  setText(

    "controlStatus",

    mapped.label

  );



  updateIndicatorText(

    "API",

    mapped.api

  );



  updateIndicatorText(

    "CONTROL PLANE",

    mapped.control

  );



  updateIndicatorText(

    "AWS",

    mapped.aws

  );

}



function updateIndicatorText(

  label,

  state

) {

  const elements = [

    ...document.querySelectorAll(

      "header *, .command-header *, .topbar *, .top-header *, .system-status *, .status-strip *"

    )

  ];



  const matches = [];



  elements.forEach(

    element => {

      if (

        element.children.length >

        0

      ) {

        return;

      }



      const text =

        normalizeLabel(

          element.textContent

        ).toUpperCase();



      if (

        text === label ||

        text.startsWith(

          `${label} `

        )

      ) {

        matches.push(

          element

        );

      }

    }

  );



  matches.forEach(

    element => {

      /*

       * Keep the existing visual label.

       * Add the operational state only if

       * a dedicated status value already exists.

       */

      const parent =

        element.parentElement;



      if (!parent) {

        return;

      }



      const stateElement =

        parent.querySelector(

          ".status-value, .indicator-value, .status-state"

        );



      if (stateElement) {

        stateElement.textContent =

          state;

      }



      parent.dataset.aegisState =

        state;

    }

  );

}





/* =========================================================

   SIDEBAR NAVIGATION

   \========================================================= */



const NAVIGATION_MAP = {

  "Command Center": [

    ".main-content"

  ],



  "Active Events": [

    ".incident-panel"

  ],



  "Network Risk": [

    ".risk-intelligence-panel",

    ".risk-panel",

    ".incident-panel"

  ],



  "Capacity & Workload": [

    ".telemetry-strip",

    ".metrics-strip",

    ".telemetry-grid"

  ],



  "Risk Intelligence": [

    ".risk-intelligence-panel",

    ".risk-panel",

    ".incident-panel"

  ],



  "Simulations": [

    ".simulation-panel"

  ],



  "AI Decision Engine": [

    ".ai-brief-panel",

    ".ai-decision-panel",

    ".intelligence-panel"

  ],



  "Interventions": [

    "#guardianApprovalConsole",

    ".simulation-panel"

  ],



  "Outcomes": [

    ".outcome-grid",

    ".prediction-evaluation-panel"

  ]

};



const NAVIGATION_HEADINGS = {

  "Command Center": [

    "COMMAND CENTER",

    "LAST-MILE OPERATIONS",

    "OPERATIONS CONTROL"

  ],



  "Active Events": [

    "ACTIVE EVENTS",

    "ACTIVE EVENT",

    "CURRENT INCIDENT",

    "INCIDENT"

  ],



  "Network Risk": [

    "NETWORK RISK",

    "RISK OVERVIEW",

    "NETWORK RISK INTELLIGENCE"

  ],



  "Capacity & Workload": [

    "CAPACITY & WORKLOAD",

    "NETWORK TELEMETRY",

    "CAPACITY",

    "WORKLOAD"

  ],



  "Risk Intelligence": [

    "RISK INTELLIGENCE",

    "RISK DRIVERS",

    "RISK ANALYSIS"

  ],



  "Simulations": [

    "SIMULATIONS",

    "INTERVENTION SIMULATION",

    "SCENARIO SIMULATION"

  ],



  "AI Decision Engine": [

    "AI DECISION ENGINE",

    "AI OPERATIONAL BRIEF",

    "AI INTELLIGENCE"

  ],



  "Interventions": [

    "INTERVENTIONS",

    "HUMAN REVIEW GATE",

    "INTERVENTION APPROVAL"

  ],



  "Outcomes": [

    "OUTCOMES",

    "PREDICTION VS ACTUAL",

    "MEASURED OUTCOME"

  ]

};



function navigationLabel(

  button

) {

  const explicit =

    button.getAttribute(

      "data-nav-label"

    ) ||

    button.getAttribute(

      "aria-label"

    );



  const nested =

    button.querySelector(

      ".nav-label, .nav-text, .nav-title, .sidebar-label"

    );



  return normalizeLabel(

    explicit ||

      (

        nested

          ? nested.textContent

          : button.textContent

      )

  );

}



function navigationTarget(

  label

) {

  for (

    const selector of

      NAVIGATION_MAP[label] || []

  ) {    const target =

      document.querySelector(

        selector

      );



    if (target) {

      return target;

    }

  }



  const candidates =

    NAVIGATION_HEADINGS[label] ||

    [];



  const headings =

    document.querySelectorAll(

      "h1,h2,h3,h4,.panel-kicker,.section-title"

    );



  for (

    const heading of headings

  ) {

    const text =

      normalizeLabel(

        heading.textContent

      ).toUpperCase();



    if (

      candidates.includes(

        text

      )

    ) {

      return (

        heading.closest(

          "section,article,.panel,.card,.grid-item"

        ) ||

        heading.parentElement ||

        heading

      );

    }

  }



  return null;

}



function navigationButtons() {

  return [

    ...document.querySelectorAll(

      ".nav-item"

    )

  ];

}



function setActiveNavigation(

  button

) {

  navigationButtons().forEach(

    item => {

      const active =

        item === button;



      item.classList.toggle(

        "active",

        active

      );



      if (active) {

        item.setAttribute(

          "aria-current",

          "page"

        );

      } else {

        item.removeAttribute(

          "aria-current"

        );

      }

    }

  );

}



function scrollToTarget(

  target

) {

  if (!target) {

    return;

  }



  const header =

    document.querySelector(

      ".command-header,.topbar,.header,header"

    );



  const offset =

    (

      header?.getBoundingClientRect()

        .height || 0

    ) + 24;



  const top =

    window.scrollY +

    target.getBoundingClientRect()

      .top -

    offset;



  window.scrollTo({

    top: Math.max(

      0,

      top

    ),

    behavior: "smooth"

  });

}



function activateNavigation(

  button,

  target

) {

  if (!target) {

    return;

  }



  setActiveNavigation(

    button

  );



  scrollToTarget(

    target

  );



  console.log(

    "AEGIS navigation:",

    navigationLabel(

      button

    )

  );

}



function initializeNavigationObserver(

  entries

) {

  navigationObserver?.disconnect();



  if (

    !entries.length ||

    !(

      "IntersectionObserver" in

      window

    )

  ) {

    return;

  }



  navigationObserver =

    new IntersectionObserver(

      visible => {

        const candidates =

          visible

            .filter(

              entry =>

                entry.isIntersecting

            )

            .sort(

              (a, b) =>

                b.intersectionRatio -

                a.intersectionRatio

            );



        if (

          !candidates.length

        ) {

          return;

        }



        const match =

          entries.find(

            item =>

              item.target ===

              candidates[0].target

          );



        if (match) {

          setActiveNavigation(

            match.button

          );

        }

      },

      {

        root: null,

        rootMargin:

          "-18% 0px -65% 0px",

        threshold: [

          0,

          0.15,

          0.35,

          0.6

        ]

      }

    );



  entries.forEach(

    item =>

      navigationObserver.observe(

        item.target

      )

  );

}



function initializeNavigation() {

  const buttons =

    navigationButtons();



  if (!buttons.length) {

    console.warn(

      "AEGIS: no .nav-item elements found."

    );



    return;

  }



  const entries = [];



  buttons.forEach(

    button => {

      if (

        button.dataset

          .aegisNavigationBound ===

        "true"

      ) {

        return;

      }



      const label =

        navigationLabel(

          button

        );



      const target =

        navigationTarget(

          label

        );



      button.setAttribute(

        "role",

        "button"

      );



      button.setAttribute(

        "tabindex",

        "0"

      );



      button.dataset

        .aegisNavigationBound =

        "true";



      if (!target) {

        button.classList.add(

          "nav-item-disabled"

        );



        return;

      }



      button.classList.remove(

        "nav-item-disabled"

      );



      entries.push({

        button,

        target

      });



      button.addEventListener(

        "click",

        event => {

          event.preventDefault();



          activateNavigation(

            button,

            target

          );

        }

      );



      button.addEventListener(

        "keydown",

        event => {

          if (

            event.key !==

              "Enter" &&

            event.key !== " "

          ) {

            return;

          }



          event.preventDefault();



          activateNavigation(

            button,

            target

          );

        }

      );

    }

  );



  initializeNavigationObserver(

    entries

  );



  const initial =

    buttons.find(

      button =>

        button.classList.contains(

          "active"

        )

    ) ||

    buttons.find(

      button =>

        navigationLabel(

          button

        ) === "Command Center"

    );



  if (initial) {

    setActiveNavigation(

      initial

    );

  }



  console.log(

    `AEGIS: ${entries.length} sidebar items interactive.`

  );

}





/* =========================================================

   CONTROL LOOP

   \========================================================= */



function getLoopSteps() {

  return [

    ...document.querySelectorAll(

      ".loop-step"

    )

  ];

}



function getLoopStepByName(

  name

) {

  const normalized =

    String(name || "")

      .trim()

      .toUpperCase();



  return getLoopSteps().find(

    step => {

      const title =

        step.querySelector(

          ".loop-title"

        );



      return (

        title &&

        title.textContent

          .trim()

          .toUpperCase() ===

          normalized

      );

    }

  );

}



function resetControlLoop() {

  getLoopSteps().forEach(

    step => {

      step.classList.remove(

        "loop-active",

        "loop-complete",

        "loop-locked"

      );



      const title =

        step.querySelector(

          ".loop-title"

        );



      if (!title) {

        return;

      }



      const name =

        title.textContent

          .trim()

          .toUpperCase();



      if (

        [

          "ACT",

          "MEASURE"

        ].includes(name)

      ) {

        step.classList.add(

          "loop-locked"

        );

      }

    }

  );

}



function setLoopStage(

  activeStage,

  completedStages = [],

  lockedStages = []

) {

  const completed =

    new Set(

      completedStages.map(

        value =>

          String(value)

            .trim()

            .toUpperCase()

      )

    );



  const locked =

    new Set(

      lockedStages.map(

        value =>

          String(value)

            .trim()

            .toUpperCase()

      )

    );



  getLoopSteps().forEach(

    step => {

      const title =

        step.querySelector(

          ".loop-title"

        );



      if (!title) {

        return;

      }



      const name =

        title.textContent

          .trim()

          .toUpperCase();



      step.classList.remove(

        "loop-active",

        "loop-complete",

        "loop-locked"

      );



      if (

        completed.has(name)

      ) {

        step.classList.add(

          "loop-complete"

        );

      }



      if (

        name ===

        String(

          activeStage || ""

        )

          .trim()

          .toUpperCase()

      ) {

        step.classList.add(

          "loop-active"

        );

      }



      if (

        locked.has(name)

      ) {

        step.classList.add(

          "loop-locked"

        );

      }

    }

  );

}



function updateControlLoopForReady() {

  resetControlLoop();



  setLoopStage(

    "SENSE",

    [],

    [

      "ACT",

      "MEASURE"

    ]  );



  const sense =

    getLoopStepByName(

      "SENSE"

    );



  if (sense) {

    const description =

      sense.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        "Ready to detect";

    }

  }



  const understand =

    getLoopStepByName(

      "UNDERSTAND"

    );



  if (understand) {

    const description =

      understand.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        "Awaiting signal";

    }

  }



  const simulate =

    getLoopStepByName(

      "SIMULATE"

    );



  if (simulate) {

    const description =

      simulate.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        "Awaiting event";

    }

  }



  const decide =

    getLoopStepByName(

      "DECIDE"

    );



  if (decide) {

    const description =

      decide.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        "Awaiting strategy";

    }

  }



  const review =

    getLoopStepByName(

      "HUMAN REVIEW"

    );



  if (review) {

    const description =

      review.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        "Approval required";

    }

  }

}



function updateControlLoopForAnalysis() {

  setLoopStage(

    "SIMULATE",

    [

      "SENSE",

      "UNDERSTAND"

    ],

    [

      "ACT",

      "MEASURE"

    ]

  );



  const stages = [

    [

      "SENSE",

      "Detecting disruption"

    ],

    [

      "UNDERSTAND",

      "Assessing network state"

    ],

    [

      "SIMULATE",

      "Evaluating alternatives"

    ],

    [

      "DECIDE",

      "Selecting intervention"

    ]

  ];



  stages.forEach(

    ([name, description]) => {

      const step =

        getLoopStepByName(

          name

        );



      if (!step) {

        return;

      }



      const descriptionElement =

        step.querySelector(

          ".loop-description"

        );



      if (

        descriptionElement

      ) {

        descriptionElement.textContent =

          description;

      }

    }

  );

}



function updateControlLoopForApproval(

  strategy

) {

  setLoopStage(

    "HUMAN REVIEW",

    [

      "SENSE",

      "UNDERSTAND",

      "SIMULATE",

      "DECIDE"

    ],

    [

      "ACT",

      "MEASURE"

    ]

  );



  const decide =

    getLoopStepByName(

      "DECIDE"

    );



  if (decide) {

    const description =

      decide.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        `${String(strategy || "INTERVENTION")

          .replaceAll("_", " ")

          .toUpperCase()} selected`;

    }

  }



  const review =

    getLoopStepByName(

      "HUMAN REVIEW"

    );



  if (review) {

    const description =

      review.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        "Operator authorization required";

    }

  }

}



function updateControlLoopForExecution() {

  setLoopStage(

    "MEASURE",

    [

      "SENSE",

      "UNDERSTAND",

      "SIMULATE",

      "DECIDE",

      "HUMAN REVIEW",

      "ACT"

    ],

    []

  );



  const review =

    getLoopStepByName(

      "HUMAN REVIEW"

    );



  if (review) {

    const description =

      review.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        "Approval recorded";

    }

  }



  const act =

    getLoopStepByName(

      "ACT"

    );



  if (act) {

    const description =

      act.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        "Intervention executed";

    }

  }



  const measure =

    getLoopStepByName(

      "MEASURE"

    );



  if (measure) {

    const description =

      measure.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        "Evaluating outcome";

    }

  }

}





/* =========================================================

   EVENT + RISK RENDERING

   \========================================================= */



function renderEvent(

  data

) {

  const event =

    data?.event;



  const station =

    data?.station;



  if (

    !event ||

    !station

  ) {

    return;

  }



  const title =

    String(

      event.event_type ||

        "EVENT"

    )

      .replaceAll(

        "_",

        " "

      )

      .replace(

        /\b\w/g,

        c =>

          c.toUpperCase()

      );



  setText(

    "eventTitle",

    title

  );



  setText(

    "severityBadge",

    event.severity ||

      "UNKNOWN"

  );



  setText(

    "stationCity",

    station.city ||

      "—"

  );



  setText(

    "stationRegion",

    station.region ||

      "—"

  );



  setText(

    "capacity",

    formatNumber(

      station.capacity

    )

  );



  setText(

    "currentLoad",

    formatNumber(

      station.current_load

    )

  );



  setText(

    "activeRoutes",

    formatNumber(

      station.active_routes

    )

  );



  setText(

    "activeNode",

    station.station_id ||

      "—"

  );



  setText(

    "networkMode",

    "INDIA / SIMULATION"

  );

}



function renderRisk(

  risk

) {

  if (!risk) {

    return;

  }



  const score =

    Number(

      risk.risk_score

    );



  const utilization =

    Number(

      risk.utilization

    );



  setText(

    "networkRisk",

    Number.isFinite(

      score

    )

      ? score.toFixed(2)

      : "—"

  );



  setText(

    "networkRiskStatus",

    risk.risk_level ||

      "UNKNOWN"

  );



  setText(

    "networkUtilization",

    Number.isFinite(

      utilization

    )

      ? `${utilization.toFixed(

          2

        )}%`

      : "—"

  );



  setText(

    "utilization",

    Number.isFinite(

      utilization

    )

      ? `${utilization.toFixed(

          2

        )}%`

      : "—"

  );



  setText(

    "riskScore",

    Number.isFinite(

      score

    )

      ? `${score.toFixed(

          2

        )} / 100`

      : "—"

  );



  const bar =

    $("riskBar");



  if (bar) {

    const width =

      Number.isFinite(

        score

      )

        ? Math.max(

            0,

            Math.min(

              100,

              score

            )

          )

        : 0;



    bar.style.width =

      `${width}%`;

  }



  const drivers =

    $("riskDrivers");



  if (

    drivers &&

    Array.isArray(

      risk.drivers

    )

  ) {

    drivers.replaceChildren();



    risk.drivers.forEach(

      driver => {

        const item =

          document.createElement(

            "div"

          );



        item.className =

          "driver";



        const marker =

          document.createElement(

            "span"

          );



        marker.textContent =

          "•";



        item.append(

          marker,

          document.createTextNode(

            String(driver)

          )

        );



        drivers.appendChild(

          item

        );

      }

    );

  }



  setText(

    "activeEvents",

    "01"

  );



  setText(

    "loadAtRisk",

    Number.isFinite(

      Number(

        currentAssessment

          ?.station

          ?.current_load

      )    )

      ? formatNumber(

          currentAssessment

            .station

            .current_load

        )

      : "—"

  );

}





/* =========================================================

   SCENARIO INTERACTION

   \========================================================= */



function getScenarioCard(

  strategy

) {

  const normalized =

    normalizeStrategy(

      strategy

    );



  return [

    ...document.querySelectorAll(

      ".scenario-card"

    )

  ].find(

    card => {

      const heading =

        card.querySelector(

          "h3"

        );



      return (

        heading &&

        normalizeStrategy(

          heading.textContent

        ) ===

          normalized

      );

    }

  );

}



function selectScenarioCard(

  strategy

) {

  const cards =

    document.querySelectorAll(

      ".scenario-card"

    );



  cards.forEach(

    card => {

      card.classList.remove(

        "scenario-selected"

      );



      card.setAttribute(

        "aria-selected",

        "false"

      );

    }

  );



  const selected =

    getScenarioCard(

      strategy

    );



  if (!selected) {

    return;

  }



  selected.classList.add(

    "scenario-selected"

  );



  selected.setAttribute(

    "aria-selected",

    "true"

  );



  const decide =

    getLoopStepByName(

      "DECIDE"

    );



  if (decide) {

    const description =

      decide.querySelector(

        ".loop-description"

      );



    if (description) {

      description.textContent =

        `${String(strategy)

          .replaceAll(

            "_",

            " "

          )

          .toUpperCase()} selected`;

    }

  }

}



function initializeScenarioInteraction() {

  document

    .querySelectorAll(

      ".scenario-card"

    )

    .forEach(

      card => {

        if (

          card.dataset

            .aegisScenarioBound ===

          "true"

        ) {

          return;

        }



        const heading =

          card.querySelector(

            "h3"

          );



        if (!heading) {

          return;

        }



        const strategy =

          heading.textContent.trim();



        card.setAttribute(

          "role",

          "button"

        );



        card.setAttribute(

          "tabindex",

          "0"

        );



        card.setAttribute(

          "aria-selected",

          "false"

        );



        card.dataset

          .aegisScenarioBound =

          "true";



        const activate =

          () =>

            selectScenarioCard(

              strategy

            );



        card.addEventListener(

          "click",

          activate

        );



        card.addEventListener(

          "keydown",

          event => {

            if (

              event.key !==

                "Enter" &&

              event.key !==

                " "

            ) {

              return;

            }



            event.preventDefault();



            activate();

          }

        );

      }

    );

}





/* =========================================================

   INTERVENTION

   \========================================================= */



function renderIntervention(

  intervention

) {

  if (!intervention) {

    return;

  }



  const score =

    Number(

      intervention.decision_score

    );



  setText(

    "decisionScore",

    Number.isFinite(

      score

    )

      ? score.toFixed(2)

      : "—"

  );



  const scenarios =

    Array.isArray(

      intervention.scenarios

    )

      ? intervention.scenarios

      : [];



  scenarios.forEach(

    scenario => {

      if (!scenario) {

        return;

      }



      const risk =

        Number(

          scenario.projected_risk

        );



      const utilization =

        Number(

          scenario.projected_utilization

        );



      if (

        scenario.strategy ===

        "ROUTE_REBALANCE"

      ) {

        setText(

          "routeRisk",

          Number.isFinite(

            risk

          )

            ? risk.toFixed(2)

            : "—"

        );



        setText(

          "routeUtilization",

          percent(

            utilization

          )

        );

      }



      if (

        scenario.strategy ===

        "CAPACITY_SHIFT"

      ) {

        setText(

          "capacityRisk",

          Number.isFinite(

            risk

          )

            ? risk.toFixed(2)

            : "—"

        );



        setText(

          "capacityUtilization",

          percent(

            utilization

          )

        );

      }



      if (

        scenario.strategy ===

        "HYBRID_RESPONSE"

      ) {

        setText(

          "hybridRisk",

          Number.isFinite(

            risk

          )

            ? risk.toFixed(2)

            : "—"

        );



        setText(

          "hybridUtilization",

          percent(

            utilization

          )

        );

      }

    }

  );



  if (

    intervention.selected_strategy

  ) {

    selectScenarioCard(

      intervention.selected_strategy

    );

  }

}





/* =========================================================

   EXECUTION + OUTCOME

   \========================================================= */



function renderExecution(

  execution

) {

  if (

    execution?.status

  ) {

    setText(

      "controlStatus",

      execution.status

    );

  }

}



function renderOutcome(
  outcome,
  intervention = {}
) {
  if (!outcome) {
    return;
  }

  const baselineRisk =
    Number(
      outcome.baseline_risk
    );

  const postRisk =
    Number(
      outcome.post_intervention_risk
    );

  const reduction =
    Number(
      outcome.risk_reduction
    );

  const baselineUtilization =
    Number(
      outcome.baseline_utilization
    );

  const postUtilization =
    Number(
      outcome.post_intervention_utilization
    );

  const predictedRisk =
    Number(
      intervention.projected_risk
    );

  const predictedUtilization =
    Number(
      intervention.projected_utilization
    );

  const riskDeviation =
    Number.isFinite(
      predictedRisk
    ) &&
    Number.isFinite(
      postRisk
    )
      ? postRisk - predictedRisk
      : NaN;

  const utilizationDeviation =
    Number.isFinite(
      predictedUtilization
    ) &&
    Number.isFinite(
      postUtilization
    )
      ? postUtilization - predictedUtilization
      : NaN;

  const outcomeStatus =
    String(
      outcome.outcome_status ||
        "UNKNOWN"
    ).replaceAll(
      "_",
      " "
    );

  /* =========================================================
     MEASURED OUTCOME — BASELINE / POST-INTERVENTION
     ========================================================= */

  setText(
    "beforeRisk",
    number(
      baselineRisk
    )
  );

  setText(
    "afterRisk",
    number(
      postRisk
    )
  );

  setText(
    "riskReduction",
    percent(
      reduction
    )
  );

  setText(
    "beforeUtilization",
    percent(
      baselineUtilization
    )
  );

  setText(
    "afterUtilization",
    percent(
      postUtilization
    )
  );

  setText(
    "outcomeStatus",
    outcomeStatus
  );

  /* =========================================================
     PREDICTION → REALITY TABLE
     ========================================================= */

  setText(
    "predictedRisk",
    number(
      predictedRisk
    )
  );

  setText(
    "actualRisk",
    number(
      postRisk
    )
  );

  const riskDeviationElement =
    document.getElementById(
      "riskDeviation"
    );

  if (riskDeviationElement) {
    riskDeviationElement.textContent =
      Number.isFinite(
        riskDeviation
      )
        ? `${
            riskDeviation >= 0
              ? "+"
              : ""
          }${riskDeviation.toFixed(2)}`
        : "—";
  }

  setText(
    "predictedUtilization",
    percent(
      predictedUtilization
    )
  );

  setText(
    "actualUtilization",
    percent(
      postUtilization
    )
  );

  /*
   * The original utilization row does not have a dedicated
   * ID for its deviation cell. Locate the fourth cell of
   * the utilization row conservatively.
   */

  const predictionReality =
    document.querySelector(
      ".prediction-reality"
    );

  if (predictionReality) {
    const rows =
      predictionReality.querySelectorAll(
        ".prediction-row"
      );

    if (rows.length >= 3) {
      const utilizationRow =
        rows[2];

      const cells =
        utilizationRow.children;

      if (cells.length >= 4) {
        const deviationCell =
          cells[3];

        deviationCell.textContent =
          Number.isFinite(
            utilizationDeviation
          )
            ? `${
                utilizationDeviation >= 0
                  ? "+"
                  : ""
              }${utilizationDeviation.toFixed(2)}%`
            : "—";
      }
    }
  }

  /* Keep visible outcome badges synchronized. */

  const statusBadges =
    document.querySelectorAll(
      ".outcome-status-badge"
    );

  statusBadges.forEach(
    badge => {
      badge.textContent =
        outcomeStatus;
    }
  );
}


/* =========================================================

   AI INTELLIGENCE

   \========================================================= */



function renderIntelligence(

  intelligence

) {

  if (!intelligence) {

    return;

  }



  setText(

    "aiSummary",

    intelligence.summary ||

      "No operational brief available."

  );



  setText(

    "aiRecommendation",

    intelligence.recommended_action ||

      "No recommendation available."

  );



  updateAIState(

    "GROUNDED"

  );

}



function updateAIState(

  state

) {

  const panel =

    document.querySelector(

      ".ai-brief-panel, .ai-decision-panel, .intelligence-panel"

    );



  if (!panel) {

    return;

  }



  const possibleBadges =

    panel.querySelectorAll(

      ".badge, .status-badge, .panel-badge, .ai-status, .intelligence-status"

    );



  possibleBadges.forEach(

    badge => {

      const text =

        normalizeLabel(

          badge.textContent

        ).toUpperCase();



      if (

        [

          "GROUNDED",

          "STANDBY",

          "ANALYZING",

          "READY",

          "ERROR"

        ].includes(text)

      ) {

        badge.textContent =

          state;

      }

    }

  );



  panel.dataset.aegisState =

    state;

}



function setAIStandby() {

  updateAIState(

    "STANDBY"

  );



  setText(

    "aiSummary",

    "AEGIS is ready to assess the active disruption."

  );



  setText(

    "aiRecommendation",

    "Run an operational assessment to generate a constrained intervention."

  );

}



function setAIAnalyzing() {

  updateAIState(

    "ANALYZING"

  );



  setText(

    "aiSummary",

    "AEGIS is analyzing the active disruption and evaluating downstream operational impact."

  );



  setText(

    "aiRecommendation",

    "Evaluating intervention strategies..."

  );

}





/* =========================================================

   DASHBOARD

   \========================================================= */



function renderDashboard(

  response

) {

  if (!response) {

    return;

  }



  renderEvent(

    response

  );  renderRisk(

    response.risk

  );



  renderIntervention(

    response.intervention

  );



  renderExecution(

    response.execution

  );



  renderOutcome(

    response.outcome,

    response.intervention

  );



  renderIntelligence(

    response.intelligence

  );

}





/* =========================================================

   PREDICTION VS ACTUAL

   \========================================================= */



function predictionContainer() {

  let container =

    $("predictionVsActual");



  if (container) {

    return container;

  }



  container =

    document.querySelector(

      ".prediction-evaluation-panel"

    );



  if (container) {

    container.id =

      "predictionVsActual";



    return container;

  }



  for (

    const heading of

      document.querySelectorAll(

        "h1,h2,h3,h4"

      )

  ) {

    if (

      heading.textContent

        .trim()

        .toLowerCase()

        .includes(

          "prediction vs actual"

        )

    ) {

      container =

        heading.closest(

          "section,article,.panel,.card"

        ) ||

        heading.parentElement;



      if (container) {

        container.id =

          "predictionVsActual";



        return container;

      }

    }

  }



  return null;

}



function clearPredictionVsActual() {

  const container =

    predictionContainer();



  if (!container) {

    return;

  }



  /*

   * Keep the original HTML panel visible,

   * but reset its values when possible.

   *

   * If the panel is dynamically created,

   * it remains hidden until execution.

   */



  const existingRows =

    container.querySelectorAll(

      "[data-prediction-value]"

    );



  existingRows.forEach(

    element => {

      element.textContent =

        "—";

    }

  );



  const generated =

    container.querySelector(

      ".prediction-generated-content"

    );



  if (generated) {

    generated.remove();

  }



  if (

    container.dataset

      .aegisGenerated ===

    "true"

  ) {

    container.hidden =

      true;

  }

}



function renderPredictionVsActual(

  response

) {

  if (!response) {

    return;

  }



  const outcome =

    response.outcome ||

    {};



  const intervention =

    response.intervention ||

    {};



  const predictedRisk =

    Number(

      intervention.projected_risk

    );



  const actualRisk =

    Number(

      outcome.post_intervention_risk

    );



  const predictedUtilization =

    Number(

      intervention.projected_utilization

    );



  const actualUtilization =

    Number(

      outcome.post_intervention_utilization

    );



  const deviation =

    Number.isFinite(

      predictedRisk

    ) &&

    Number.isFinite(

      actualRisk

    )

      ? actualRisk -

        predictedRisk

      : NaN;



  const outcomeStatus =

    outcome.outcome_status ||

    "UNKNOWN";



  const effectiveness =

    Number(

      outcome.effectiveness_score

    );



  let container =

    predictionContainer();



  if (!container) {

    container =

      document.createElement(

        "section"

      );



    container.id =

      "predictionVsActual";



    container.className =

      "prediction-evaluation-panel panel";



    const outcomePanel =

      document.querySelector(

        ".outcome-grid"

      );



    if (outcomePanel) {

      outcomePanel.insertAdjacentElement(

        "afterend",

        container

      );

    } else {

      document

        .querySelector(

          ".main-content"

        )

        ?.appendChild(

          container

        );

    }

  }



  container.hidden =

    false;



  container.className =

    "prediction-evaluation-panel panel";



  container.dataset

    .aegisGenerated =

    "true";



  container.innerHTML = `

    <div class="prediction-evaluation-header prediction-generated-content">

      <div>

        <span class="panel-kicker">

          CLOSED-LOOP EVALUATION

        </span>



        <h2>

          Prediction vs Actual

        </h2>



        <p>

          AEGIS compares its counterfactual projection

          with the measured operational state after execution.

        </p>

      </div>



      <div class="prediction-evaluation-badge">

        ${String(

          outcomeStatus

        ).replaceAll(

          "_",

          " "

        )}

      </div>

    </div>



    <div class="prediction-evaluation-grid prediction-generated-content">



      <article class="prediction-card">

        <div class="prediction-card-label">

          MODEL PROJECTION

        </div>



        <div class="prediction-card-title">

          PREDICTED

        </div>



        <div class="prediction-card-value">

          ${number(

            predictedRisk

          )}

        </div>



        <div class="prediction-card-unit">

          projected risk

        </div>



        <div class="prediction-card-secondary">

          <span>

            UTILIZATION

          </span>



          <strong>

            ${percent(

              predictedUtilization

            )}

          </strong>

        </div>

      </article>



      <div class="prediction-evaluation-arrow">

        →

      </div>



      <article class="prediction-card prediction-card-actual">

        <div class="prediction-card-label">

          MEASURED STATE

        </div>



        <div class="prediction-card-title">

          ACTUAL

        </div>



        <div class="prediction-card-value">

          ${number(

            actualRisk

          )}

        </div>



        <div class="prediction-card-unit">

          measured risk

        </div>



        <div class="prediction-card-secondary">

          <span>

            UTILIZATION

          </span>



          <strong>

            ${percent(

              actualUtilization

            )}

          </strong>

        </div>

      </article>



      <article class="prediction-deviation-card">

        <div class="prediction-card-label">

          PREDICTION DEVIATION

        </div>



        <strong>

          ${

            Number.isFinite(

              deviation

            )

              ? `${

                  deviation >= 0

                    ? "+"

                    : ""

                }${deviation.toFixed(

                  2

                )}`

              : "—"

          }

        </strong>



        <span>

          risk points

        </span>

      </article>



      <article class="prediction-outcome-card">

        <div class="prediction-card-label">

          OUTCOME

        </div>



        <strong>

          ${String(

            outcomeStatus

          ).replaceAll(

            "_",

            " "

          )}

        </strong>



        <span>

          Effectiveness ${

            Number.isFinite(

              effectiveness

            )

              ? effectiveness.toFixed(

                  2

                )

              : "—"

          } / 100

        </span>

      </article>



    </div>

  `;

}





/* =========================================================

   HUMAN APPROVAL CONSOLE

   \========================================================= */



function getApprovalConsole() {

  let el =

    $("guardianApprovalConsole");



  if (el) {

    return el;

  }



  el =

    document.createElement(

      "section"

    );



  el.id =

    "guardianApprovalConsole";



  el.className =

    "guardian-approval-console";



  const panel =

    document.querySelector(

      ".simulation-panel"

    );



  if (panel) {

    panel.insertAdjacentElement(

      "afterend",

      el

    );

  } else {

    document

      .querySelector(

        ".main-content"

      )

      ?.appendChild(

        el

      );

  }



  return el;

}



function renderApprovalConsole(

  assessment

) {

  const el =

    getApprovalConsole();



  if (!el) {

    return;

  }



  const intervention =

    assessment?.intervention ||

    {};



  const risk =

    assessment?.risk ||

    {};



  const status =

    assessment?.status ||

    "UNKNOWN";



  const strategy =

    String(

      intervention.selected_strategy ||

        "UNKNOWN"

    ).replaceAll(

      "_",

      " "

    );



  const baselineRisk =

    Number(

      intervention.baseline_risk ??

        risk.risk_score

    );



  const projectedRisk =

    Number(

      intervention.projected_risk

    );



  const baselineUtilization =

    Number(

      intervention.baseline_utilization ??

        risk.utilization

    );



  const projectedUtilization =

    Number(

      intervention.projected_utilization

    );



  const decisionScore =

    Number(

      intervention.decision_score

    );



  const safetyPassed =

    intervention.safety_checks_passed;



  el.innerHTML = `

    <div class="approval-console-header">

      <div>



        <span class="approval-console-kicker">

          HUMAN REVIEW GATE

        </span>



        <h2>

          Intervention Approval Required

        </h2>        <p>

          AEGIS has assessed the disruption and selected

          a constrained intervention. No operational action

          has been executed.

        </p>



      </div>



      <div class="approval-status-badge">

        ${String(

          status

        ).replaceAll(

          "_",

          " "

        )}

      </div>

    </div>



    <div class="approval-console-grid">



      <div class="approval-metric">

        <span>

          RISK

        </span>



        <strong>

          ${number(

            baselineRisk

          )}

        </strong>



        <small>

          ${

            risk.risk_level ||

            "UNKNOWN"

          }

        </small>

      </div>



      <div class="approval-metric">

        <span>

          RECOMMENDED ACTION

        </span>



        <strong>

          ${strategy}

        </strong>



        <small>

          Decision score:

          ${

            Number.isFinite(

              decisionScore

            )

              ? decisionScore.toFixed(

                  2

                )

              : "—"

          }

        </small>

      </div>



      <div class="approval-metric">

        <span>

          PROJECTED RISK

        </span>



        <strong>

          ${number(

            baselineRisk

          )}

          →

          ${number(

            projectedRisk

          )}

        </strong>



        <small>

          Counterfactual projection

        </small>

      </div>



      <div class="approval-metric">

        <span>

          UTILIZATION

        </span>



        <strong>

          ${percent(

            baselineUtilization

          )}

          →

          ${percent(

            projectedUtilization

          )}

        </strong>



        <small>

          Projected operational state

        </small>

      </div>



    </div>



    <div class="approval-console-footer">



      <div class="approval-safety">



        <span class="safety-indicator">

          ${

            safetyPassed

              ? "✓"

              : "!"

          }

        </span>



        <div>

          <strong>

            Safety Checks

          </strong>



          <span>

            ${

              safetyPassed

                ? "PASSED"

                : "REVIEW REQUIRED"

            }

          </span>

        </div>



      </div>



      <button

        id="approveExecuteButton"

        class="approval-execute-button"

        type="button"

        ${

          status !==

          "AWAITING_HUMAN_APPROVAL"

            ? "disabled"

            : ""

        }

      >

        APPROVE & EXECUTE

      </button>



    </div>

  `;



  const button =

    $("approveExecuteButton");



  if (

    button &&

    status ===

      "AWAITING_HUMAN_APPROVAL"

  ) {

    button.addEventListener(

      "click",

      approveGuardianIntervention

    );

  }



  updateControlLoopForApproval(

    intervention.selected_strategy

  );



  setAIStateAfterAssessment(

    assessment

  );

}



function setAIStateAfterAssessment(

  assessment

) {

  const intelligence =

    assessment?.intelligence;



  if (intelligence) {

    renderIntelligence(

      intelligence

    );



    return;

  }



  updateAIState(

    "GROUNDED"

  );



  setText(

    "aiSummary",

    "Assessment complete. AEGIS has evaluated the active disruption and constrained intervention options."

  );



  setText(

    "aiRecommendation",

    String(

      assessment?.intervention

        ?.selected_strategy ||

        "INTERVENTION"

    ).replaceAll(

      "_",

      " "

    )

  );

}



function renderExecutedApprovalState(

  response

) {

  const el =

    getApprovalConsole();



  if (!el) {

    return;

  }



  const execution =

    response?.execution ||

    {};



  const outcome =

    response?.outcome ||

    {};



  el.innerHTML = `

    <div class="approval-console-header">



      <div>



        <span class="approval-console-kicker">

          HUMAN REVIEW GATE

        </span>



        <h2>

          Intervention Executed

        </h2>



        <p>

          The approved intervention has been executed

          and measured by AEGIS.

        </p>



      </div>



      <div class="approval-status-badge approval-status-executed">

        EXECUTED

      </div>



    </div>



    <div class="approval-console-grid">



      <div class="approval-metric">



        <span>

          EXECUTION ID

        </span>



        <strong>

          ${

            execution.execution_id ||

            "—"

          }

        </strong>



        <small>

          ${

            execution.status ||

            "UNKNOWN"

          }

        </small>



      </div>



      <div class="approval-metric">



        <span>

          RISK

        </span>



        <strong>

          ${number(

            outcome.baseline_risk

          )}

          →

          ${number(

            outcome.post_intervention_risk

          )}

        </strong>



        <small>

          ${

            percent(

              outcome.risk_reduction

            )

          }

          reduction

        </small>



      </div>



      <div class="approval-metric">



        <span>

          UTILIZATION

        </span>



        <strong>

          ${percent(

            outcome.baseline_utilization

          )}

          →

          ${percent(

            outcome.post_intervention_utilization

          )}

        </strong>



        <small>

          Measured operational state

        </small>



      </div>



      <div class="approval-metric">



        <span>

          OUTCOME

        </span>



        <strong>

          ${String(

            outcome.outcome_status ||

              "UNKNOWN"

          ).replaceAll(

            "_",

            " "

          )}

        </strong>



        <small>

          Effectiveness ${

            Number.isFinite(

              Number(

                outcome.effectiveness_score

              )

            )

              ? Number(

                  outcome.effectiveness_score

                ).toFixed(

                  2

                )

              : "—"

          } / 100

        </small>



      </div>



    </div>



    <div class="approval-console-footer">



      <div class="approval-safety">



        <span class="safety-indicator">

          ✓

        </span>



        <div>



          <strong>

            Human Approval Recorded

          </strong>



          <span>

            Intervention executed successfully

          </span>



        </div>



      </div>



    </div>

  `;



  updateControlLoopForExecution();

}





/* =========================================================

   INITIAL DASHBOARD STATE

   \========================================================= */



function initializeDashboardState() {

  currentAssessmentId =

    null;



  currentAssessment =

    null;



  approvalInProgress =

    false;



  assessmentInProgress =

    false;



  setSystemStatus(

    SYSTEM_STATE.READY

  );



  updateOperationalIndicators(

    SYSTEM_STATE.READY

  );



  updateControlLoopForReady();



  setAIStandby();



  /*

   * Do not display stale prediction data

   * before an intervention has actually run.

   */

  clearPredictionVsActual();



  /*

   * Keep the approval area in a deliberate

   * standby state instead of making it look broken.

   */

  const consoleElement =

    getApprovalConsole();



  if (consoleElement) {

    consoleElement.innerHTML = `

      <div class="approval-console-header">



        <div>



          <span class="approval-console-kicker">

            HUMAN DECISION GATE

          </span>



          <h2>

            Awaiting operational assessment

          </h2>



          <p>

            AEGIS will present a constrained intervention

            here before execution.

          </p>



        </div>



        <div class="approval-status-badge">

          STANDBY

        </div>



      </div>

    `;

  }

}





/* =========================================================

   AWS ASSESSMENT

   \========================================================= */



async function assessGuardianState() {

  if (

    assessmentInProgress ||

    approvalInProgress

  ) {

    return;

  }



  const refreshButton =

    $("refreshButton");



  assessmentInProgress =

    true;



  try {

    if (refreshButton) {

      refreshButton.textContent =

        "↻ Analyzing...";



      refreshButton.disabled =

        true;

    }



    setSystemStatus(

      SYSTEM_STATE.ANALYZING

    );



    updateOperationalIndicators(

      SYSTEM_STATE.ANALYZING

    );



    updateControlLoopForAnalysis();    setAIAnalyzing();



    /*

     * Clear any previous execution state

     * before a new assessment.

     */

    clearPredictionVsActual();



    setText(

      "beforeRisk",

      "—"

    );



    setText(

      "afterRisk",

      "—"

    );



    setText(

      "riskReduction",

      "—"

    );



    const response =

      await fetch(

        ASSESS_EVENT_ENDPOINT,

        {

          method:

            "POST",



          headers: {

            "Content-Type":

              "application/json",



            Accept:

              "application/json"

          },



          body:

            JSON.stringify(

              DEMO_REQUEST

            )

        }

      );



    if (!response.ok) {

      throw new Error(

        `AEGIS API returned HTTP ${response.status}`

      );

    }



    const payload =

      await response.json();



    if (!payload.success) {

      throw new Error(

        "AEGIS API returned an unsuccessful assessment."

      );

    }



    const assessment =

      payload.data;



    if (

      !assessment?.assessment_id

    ) {

      throw new Error(

        "AEGIS assessment response did not contain an assessment ID."

      );

    }



    currentAssessmentId =

      assessment.assessment_id;



    currentAssessment =

      assessment;



    console.log(

      "AEGIS assessment:",

      payload

    );



    renderEvent(

      assessment

    );



    renderRisk(

      assessment.risk

    );



    renderIntervention(

      assessment.intervention

    );



    renderApprovalConsole(

      assessment

    );



    setSystemStatus(

      SYSTEM_STATE.AWAITING_APPROVAL

    );



    updateOperationalIndicators(

      SYSTEM_STATE.AWAITING_APPROVAL

    );



    updateControlLoopForApproval(

      assessment

        ?.intervention

        ?.selected_strategy

    );



    setAIStateAfterAssessment(

      assessment

    );



    setText(

      "controlStatus",

      "AWAITING APPROVAL"

    );



  } catch (error) {

    console.error(

      "AEGIS assessment error:",

      error

    );



    setSystemStatus(

      SYSTEM_STATE.ERROR

    );



    updateOperationalIndicators(

      SYSTEM_STATE.ERROR

    );



    updateControlLoopForReady();



    updateAIState(

      "ERROR"

    );



    setText(

      "aiSummary",

      "AEGIS could not complete the operational assessment."

    );



    setText(

      "aiRecommendation",

      "Check the AWS API connection and retry."

    );



    /*

     * Avoid an aggressive browser alert.

     * The dashboard itself communicates the failure.

     */

    console.warn(

      "AEGIS: assessment failed. Retry from RUN ASSESSMENT."

    );



  } finally {

    assessmentInProgress =

      false;



    if (refreshButton) {

      refreshButton.textContent =

        "↻ Run Assessment";



      refreshButton.disabled =

        false;

    }

  }

}





/* =========================================================

   HUMAN APPROVAL + EXECUTION

   \========================================================= */



async function approveGuardianIntervention() {

  if (!currentAssessmentId) {

    alert(

      "There is no pending AEGIS assessment to approve."

    );



    return;

  }



  if (

    approvalInProgress ||

    assessmentInProgress

  ) {

    return;

  }



  approvalInProgress =

    true;



  const button =

    $("approveExecuteButton");



  try {

    if (button) {

      button.disabled =

        true;



      button.textContent =

        "EXECUTING...";

    }



    setSystemStatus(

      SYSTEM_STATE.EXECUTING

    );



    updateOperationalIndicators(

      SYSTEM_STATE.EXECUTING

    );



    setLoopStage(

      "ACT",

      [

        "SENSE",

        "UNDERSTAND",

        "SIMULATE",

        "DECIDE",

        "HUMAN REVIEW"

      ],

      [

        "MEASURE"

      ]

    );



    const response =

      await fetch(

        approveEndpoint(

          currentAssessmentId

        ),

        {

          method:

            "POST",



          headers: {

            "Content-Type":

              "application/json",



            Accept:

              "application/json"

          },



          body:

            JSON.stringify({

              approved:

                true

            })

        }

      );



    if (!response.ok) {

      throw new Error(

        `AEGIS approval returned HTTP ${response.status}`

      );

    }



    const payload =

      await response.json();



    if (!payload.success) {

      throw new Error(

        "AEGIS API returned an unsuccessful execution response."

      );

    }



    const result =

      payload.data?.result ||

      payload.data;



    console.log(

      "AEGIS execution:",

      payload

    );



    renderDashboard(

      result

    );



    renderExecutedApprovalState(

      result

    );



    renderPredictionVsActual(

      result

    );



    setSystemStatus(

      SYSTEM_STATE.EXECUTED

    );



    updateOperationalIndicators(

      SYSTEM_STATE.EXECUTED

    );



    updateControlLoopForExecution();



    currentAssessment =

      result;



    /*

     * Keep the result available in memory

     * so the dashboard can continue to display it.

     *

     * Do not clear currentAssessment immediately.

     */

    currentAssessmentId =

      null;



  } catch (error) {

    console.error(

      "AEGIS execution error:",

      error

    );



    setSystemStatus(

      SYSTEM_STATE.ERROR

    );



    updateOperationalIndicators(

      SYSTEM_STATE.ERROR

    );



    if (button) {

      button.disabled =

        false;



      button.textContent =

        "APPROVE & EXECUTE";

    }



    alert(

      "AEGIS could not execute the approved intervention."

    );



  } finally {

    approvalInProgress =

      false;

  }

}





/* =========================================================

   LOAD EXISTING ASSESSMENT

   \========================================================= */



async function loadGuardianState() {

  if (!currentAssessmentId) {

    /*

     * Deliberately do not auto-run an assessment.

     * The operator explicitly starts one.

     */

    return;

  }



  try {

    const response =

      await fetch(

        assessmentEndpoint(

          currentAssessmentId

        ),

        {

          method:

            "GET",



          headers: {

            Accept:

              "application/json"

          }

        }

      );



    if (!response.ok) {

      throw new Error(

        `AEGIS state request returned HTTP ${response.status}`

      );

    }



    const payload =

      await response.json();



    if (!payload.success) {

      throw new Error(

        "AEGIS API returned an unsuccessful state response."

      );

    }



    const assessment =

      payload.data;



    currentAssessment =

      assessment;



    if (

      assessment.status ===

      "AWAITING_HUMAN_APPROVAL"

    ) {

      renderEvent(

        assessment

      );



      renderRisk(

        assessment.risk

      );



      renderIntervention(

        assessment.intervention

      );



      renderApprovalConsole(

        assessment

      );



      setSystemStatus(

        SYSTEM_STATE.AWAITING_APPROVAL

      );



      updateControlLoopForApproval(

        assessment

          ?.intervention

          ?.selected_strategy

      );



      return;

    }



    if (

      assessment.status ===

      "EXECUTED"

    ) {

      const result =

        assessment.result ||

        assessment.execution_result ||

        assessment;



      renderDashboard(

        result

      );



      renderExecutedApprovalState(

        result

      );



      renderPredictionVsActual(

        result

      );



      setSystemStatus(

        SYSTEM_STATE.EXECUTED

      );



      updateControlLoopForExecution();



      return;

    }



    renderApprovalConsole(

      assessment

    );



  } catch (error) {

    console.error(

      "AEGIS state load error:",

      error

    );



    setSystemStatus(

      SYSTEM_STATE.ERROR

    );

  }

}





/* =========================================================

   API HEALTH

   \========================================================= */



async function checkApiHealth() {

  try {

    const response =

      await fetch(

        HEALTH_ENDPOINT,

        {

          method:

            "GET",



          headers: {

            Accept:

              "application/json"

          }

        }

      );



    if (

      response.ok    ) {

      console.log(

        "AEGIS API health check: ONLINE"

      );



      updateIndicatorText(

        "API",

        "ONLINE"

      );



      updateIndicatorText(

        "AWS",

        "CONNECTED"

      );



      return true;

    }



    throw new Error(

      `Health endpoint returned HTTP ${response.status}`

    );



  } catch (error) {

    /*

     * Health check failure should not make

     * the dashboard unusable.

     *

     * The actual assessment call remains

     * the authoritative test.

     */

    console.warn(

      "AEGIS API health check unavailable:",

      error

    );



    updateIndicatorText(

      "API",

      "READY"

    );



    updateIndicatorText(

      "AWS",

      "READY"

    );



    return false;

  }

}





/* =========================================================

   REFRESH / RUN ASSESSMENT

   \========================================================= */



function initializeRefresh() {

  const refreshButton =

    $("refreshButton");



  if (!refreshButton) {

    console.warn(

      "AEGIS: refresh button not found."

    );



    return;

  }



  if (

    refreshButton.dataset

      .aegisRefreshBound ===

    "true"

  ) {

    return;

  }



  refreshButton.dataset

    .aegisRefreshBound =

    "true";



  refreshButton.textContent =

    "↻ Run Assessment";



  refreshButton.addEventListener(

    "click",

    assessGuardianState

  );

}





/* =========================================================

   RESPONSIVE / UI ENHANCEMENTS

   \========================================================= */



function initializeInteractivePanels() {

  /*

   * Make clickable dashboard cards feel intentional

   * without changing their existing behavior.

   */



  document

    .querySelectorAll(

      ".scenario-card"

    )

    .forEach(

      card => {

        card.addEventListener(

          "mouseenter",

          () => {

            card.dataset

              .aegisHover =

              "true";

          }

        );



        card.addEventListener(

          "mouseleave",

          () => {

            delete card.dataset

              .aegisHover;

          }

        );

      }

    );

}





/* =========================================================

   MAIN INITIALIZATION

   \========================================================= */



function initializeGuardianDashboard() {

  console.log(

    "AEGIS — initializing last-mile operations control tower..."

  );



  initializeNavigation();



  initializeScenarioInteraction();



  initializeInteractivePanels();



  initializeRefresh();



  initializeDashboardState();



  /*

   * Health is informational.

   * It does NOT automatically trigger an assessment.

   */

  checkApiHealth();



  console.log(

    "AEGIS — dashboard ready."

  );

}



document.addEventListener(

  "DOMContentLoaded",

  () => {

    initializeGuardianDashboard();

  }

);