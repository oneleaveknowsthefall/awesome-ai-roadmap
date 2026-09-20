---
description: Connect pretraining, compute allocation, fine-tuning, and preference optimization through their losses, data sources, resource accounting, and evaluation limits.
---

# LLM · Training and Alignment

This module covers pretraining, scaling laws, fine-tuning, LoRA, post-training, and preference optimization. It distinguishes **training objectives**, **trainable parameters**, and **feedback sources**, rather than treating them as mutually exclusive algorithms.

## Chapters

1. [Chapter 6: The Three-Stage Training Framework for LLMs](06-llm-training.md)
2. [Chapter 7: Scaling Laws and Emergent Abilities](07-scaling-law-emergence.md)
3. [Chapter 8: Fine-Tuning Approaches for LLMs](08-finetuning.md)
4. [Chapter 9: LoRA in Depth](09-lora.md)
5. [Chapter 10: A Survey of Post-Training Methods](10-post-training.md)
6. [Chapter 11: DPO vs. PPO in Depth](11-dpo-vs-ppo.md)

## Reading Guide

- **Training workflows and budgets:** Start with Chapters 6 and 7, distinguishing empirical allocation guidelines from hard rules.
- **Designing fine-tuning experiments:** Chapter 8 covers error attribution and GPU memory accounting; Chapter 9 examines LoRA initialization, merging, and deployment constraints.
- **Understanding preference optimization:** Chapter 10 maps the relationships between methods; Chapter 11 works through KL divergence, probability ratios, advantages, and the DPO derivation.
- **Applying the algorithms to multistep tool tasks:** Continue with [Agent Post-Training](../../agent/07-post-training/25-agent-post-training.md) to see how failed trajectories become training data and how to preserve capabilities that already work.

Model data volumes and training workflows refer to the original report versions cited in each chapter; they are not used to infer undisclosed details of later models. Experimental results do not establish universal memory requirements, quality rankings, or parameter-count thresholds.

Back to [LLM Topics](../README.md).
