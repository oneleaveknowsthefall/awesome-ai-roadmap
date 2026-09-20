---
description: How the handbook connects models, retrieval, tools, agents, and production delivery through engineering decisions that can be explained and tested.
---

# Preface

The difficult part of an interview is often not naming a technique but answering the next question: why? Why use retrieval rather than fine-tuning here? Why can a system still take the wrong action after validation has been added? Why might an offline score improve without making the product more useful?

Those follow-up questions guide this book. We begin with what models can do and where those capabilities come from, then move through multimodal systems, tool calling, retrieval, and agents. The later parts cover frameworks, production operations, safety, and delivery in a customer's environment. The foundations are not just an introduction: understanding the conditions a mechanism depends on is how you explain when it works and when it fails.

Different questions call for different explanations. Sometimes we need to trace a process, sometimes compare alternatives, and sometimes follow a mistake through to its consequences. There is no need to turn every chapter into an answer of the same length. Practice answering the question directly, explaining the mechanism, and then supplying the assumptions, counterexamples, and checks that a follow-up question requires.

Examples help you reason; they are not evidence of your own project experience. When discussing your work, be clear about what you actually owned, what information was available, and what remained uncertain. The hypothetical cases in this book are not material to present as personal achievements.

Terminology and product interfaces change, and our methods of evaluating systems need revision too. The aim is not only to explain a familiar design, but to recognize what must be reconsidered when its conditions change.
