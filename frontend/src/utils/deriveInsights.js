// These helpers derive display-only content from the real analysis
// response (matches + score already returned by the backend). Nothing
// here calls an AI model or invents facts about the candidate — search
// terms and question templates are generic scaffolding, not personalized
// claims, and are labeled as such in the UI.

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

// A fixed, generic 3-step sequence template — not specific to any skill's
// real learning path (that's Phase 7 scope). Presented honestly as a
// generic starting point, not a personalized curriculum.
export function learningRoadmapFor(gapMatch, audience = "seeker") {
  const skill = gapMatch.canonical_skill;
  const possessive = audience === "provider" ? "their" : "your";
  return {
    skill,
    priority: gapMatch.priority,
    searchTerms: [`beginner ${skill} tutorial`, `${skill} crash course`, `${skill} practice project ideas`],
    practiceProject: `Build a small project that specifically applies ${skill}, then describe it on ${possessive} resume with a concrete outcome.`,
    steps: ["Learn the fundamentals", "Follow a guided tutorial or course", "Apply it in a small practice project"],
  };
}

const BEHAVIORAL_QUESTIONS = [
  "Tell me about a time you had to learn a new technology quickly for a project. How did you approach it?",
  "Describe a challenging bug or technical problem you solved recently. What was your process?",
];

export function generateInterviewQuestions(analysis, jdRoleTitle) {
  const matches = analysis?.matches || [];
  const matched = sortByPriority(matches.filter((m) => m.status === "MATCH"));
  const gaps = sortByPriority(matches.filter((m) => m.status === "GAP"));
  const roleText = jdRoleTitle ? `the ${jdRoleTitle} role` : "this role";

  const technical = matched.slice(0, 5).map((m) => ({
    category: "Technical",
    question: `The job description asks for ${m.canonical_skill}, and your resume shows evidence of it. Walk me through a specific example of how you used ${m.canonical_skill}.`,
    basedOn: m.canonical_skill,
  }));

  const project = matched
    .filter((m) => m.evidence?.[0]?.evidence_type === "PROJECT")
    .slice(0, 2)
    .map((m) => ({
      category: "Project",
      question: `Tell me more about the project where you used ${m.canonical_skill}. What was your specific contribution?`,
      basedOn: m.canonical_skill,
    }));

  const behavioral = BEHAVIORAL_QUESTIONS.map((q) => ({ category: "Behavioral", question: q, basedOn: null }));

  const roleTextCapitalized = roleText.charAt(0).toUpperCase() + roleText.slice(1);
  const gapFocused = gaps.slice(0, 1).map((m) => ({
    category: "Gap-focused",
    question: `${roleTextCapitalized} also asks for ${m.canonical_skill}, which isn't clearly shown in your resume. Do you have any experience with it, even informally?`,
    basedOn: m.canonical_skill,
  }));

  return [...technical, ...project, ...behavioral, ...gapFocused];
}
