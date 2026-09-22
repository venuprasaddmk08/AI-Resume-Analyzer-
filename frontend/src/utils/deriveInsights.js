// Small display-only helpers shared across tabs. The learning roadmap and
// interview questions themselves are generated server-side (see
// services/insights_engine.py) so they can be AI-personalized when
// available; nothing here invents facts about the candidate.

const PRIORITY_LABEL = {
  MANDATORY: "Mandatory",
  PREFERRED: "Preferred",
  NICE_TO_HAVE: "Nice to have",
};

export function priorityLabel(priority) {
  return PRIORITY_LABEL[priority] || priority;
}

const PRIORITY_ORDER = { MANDATORY: 0, PREFERRED: 1, NICE_TO_HAVE: 2 };

export function sortByPriority(matches) {
  return [...matches].sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9));
}
