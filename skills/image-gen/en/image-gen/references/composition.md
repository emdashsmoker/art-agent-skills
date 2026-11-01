# Request types, substitution, and scene building

Details for the request type and composition sections of SKILL.md. Read this when classifying a request, converting a message into something drawable, or writing a scene prompt.

## Named subject test

A noun in the request that has a physical form and a recognizable outline is a named subject. Use it as the subject of the English prompt as it is, and skip substitution and consent.

- Keep a symbolic object the user specified. Specifying it means the user has already made the choice.
- If the user provides an object and a message, make the object the subject and convey the message through style and color.
- People, animals, and places are named subjects too. Examples: "a woman standing on a beach", "a cat on a desk", "a harbor at dawn".
- With the upfront workaround at maximum, a named subject may also be replaced. The replacement standard and the confirmation follow the upfront workaround section of defects.md.

## What a prompt can control

Diffusion models reflect the subject noun, style, color, background, and time of day. Counts, relations between elements, states and actions, directions, and text are rarely reflected. Substitution therefore does not attempt to reproduce them. Its goal is to convey the mood and meaning of a topic with one object or one scene.

## Substitution rules

Use substitution for message requests and diagram requests. With the upfront workaround at maximum, the same rules apply when replacing a named subject.

- Start from the message of the original request and substitute once. Do not chain substitutions by replacing a chosen stand-in with another. To change the stand-in, go back to the original message and select another candidate.
- If the stand-in is more abstract than the noun in the original request, cancel the substitution and use the original noun. Substitution turns what cannot be drawn into something that can. Moving toward abstraction makes the picture harder to recognize.
- Choose by the message. A rising-trend graph request becomes something that embodies rising. Check that the usual impression of the stand-in fits the message before you offer it.
- For icons, choose an object with a silhouette that fills the frame. Do not choose landscapes made only of air and terrain, and subjects defined by material.
- Among several candidates, select the one with the simplest, most familiar outline. Simple, common subjects give stable results.
- Convey direction and state by choosing a subject that carries that meaning itself. Phrases such as "rising" or "collapsing" are rarely reflected.
- More elements mean more omissions and misplacements, so keep elements few. Exact counts are not reflected, so do not make a count the message.
- Keep the subject description short. Limit mood words to color and time of day.
- For subjects outside the tables below, try at least two seeds before judging whether the style is reflected.

### Icon substitution examples

These are examples. If another object fits the original message better, use it.

| Message of the original request | Stand-in object |
|---|---|
| Stepwise progress, process, connection | `a bridge over calm water` |
| Growth, step-by-step rise | `a stone staircase` |
| Leap, expansion, market expansion, scale-up | `a hot air balloon` |
| Reaching a goal, top level | `a mountain peak` |
| Layers, accumulation, laying foundations | `a stone tower` |
| Spread, branching out | `a large tree` |
| Descent, declining trend, reduction, soft landing | `a parachute` |
| Lightness, cost cutting, lightening, simplification | `a feather` |
| Comparison, balance, composition, priorities | `a balance scale` |
| Finding a position, setting direction | `a compass` |
| Guidance, assessing the situation, showing the way | `a lighthouse on a rock in the sea` |
| Stability, settling, steadiness, risk management | `an anchor` |
| Unity, cooperation | `a braided rope` |
| Transition, gateway, new beginning, phase change | `a stone archway` |
| Speed, drive, smooth progress, efficiency | `a sailboat` |

### Scene substitution examples

A scene draws one metaphor as a whole scene. Element counts are hard to control, so keep one metaphor. Write the prompt as a description of the scene and add style keywords.

| Message | Metaphor | Key prompt phrase |
|---|---|---|
| Rise, growth | Stairs climbing toward a sunrise | ascending stone steps toward a sunrise sky |
| Decline, shrinkage | A downhill path with falling leaves | falling leaves over a descending path, muted tones |
| Connection, cooperation | Glowing points joined by thin lines | constellation of glowing points joined by thin lines |
| Cycle, repetition | Four seasons in a circle | circular composition of four seasons |
| Stages, journey | A trail toward the summit | winding mountain trail toward the summit |
| Hierarchy, structure | A tree with roots, trunk, and branches | a single tree with roots, trunk and branches |
| Transition, contrast | A sky split between storm and clear weather | split sky, stormy dark left and clear bright right |
| Convergence, becoming one, synergy | Two rivers merging | two rivers merging into one stream, aerial view |
| Protection, stability | A stack of stones on a calm horizon | balanced stack of stones on a calm horizon |
| Speed, dynamism, efficiency | A streamlined shape leaving trails | streamlined shape with motion trails |

## Consent for diagram requests

Present the limitations, the substitute, the output, and a request for confirmation in one message. Generate after the user agrees.

- Limitations: if drawn as requested, the diagram's text and connectors would carry no meaning. Numbers and ratios can be conveyed only as increase and decrease, more and less.
- Substitute: summarize the core message of the original request in one sentence and propose one stand-in that fits it. Example: the core message of a three-stage growth roadmap is "we climb step by step".
- Output: the result is an icon or a scene of the stand-in.
- Text: if text and numbers are needed, use the image as a background and add text on top in an editing tool.

Example:

> Diffusion models cannot render text or precise line structures. I can create your [original request] as a picture of [stand-in] that conveys [core message]. You can add the text on top of the finished picture in an editing tool. Shall I proceed?

- If the user agrees, generate with the substitute prompt. The rest of the process is the same as for a normal request.
- If the user declines, select another stand-in from the original message and propose it.

## Scene building

Scenes are most stable with two or three common elements plus a time of day and a color. Diffusion models reproduce scene types they saw often in training.

- Elements: choose common ones such as sky, sea, mountains, a road, trees, a river, a forest, a city, a village, an industrial area, a lab, an office. Four or more elements increase omissions and misplacements.
- Replace elements that point to a specific company or product with common ones. Specific products are rarely reproduced accurately.
- Time of day: select one of dawn, sunrise, noon, sunset, or night to fix the light direction and contrast.
- Color: select one color family that matches the palette of where it will be used.
- Example: a river and a city skyline at sunset with a warm orange family. Prompt: `city skyline beside a river at sunset, warm orange palette, wide horizon, watercolor illustration`
- To fit a full-body person into a wide banner, place the person in the distance or use an upper-body framing.
