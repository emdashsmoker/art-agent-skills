# Request types, substitution, and scene building

Details for the request type and composition sections of SKILL.md. Read this when sorting a request, turning a message into something drawable, or writing a scene prompt.

## Named subject test

A noun in the request that has a physical form and a recognizable outline is a named subject. Use it as the subject of the English prompt as it is, and skip substitution and consent.

- Keep a symbolic object the user named. Naming it means the user already chose.
- If the user gives an object and a message, make the object the subject and carry the message through style and color.
- People, animals, and places are named subjects too. Examples: "a woman standing on a beach", "a cat on a desk", "a harbor at dawn".

## What a prompt can control

Diffusion models reflect the subject noun, style, color, background, and time of day. Counts, relations between elements, states and actions, directions, and text rarely come through. Substitution therefore makes no attempt to reproduce them. Its goal is to carry the mood and meaning of a topic with one object or one scene.

## Substitution rules

Use substitution for message requests and diagram requests only.

- Start from the message of the original request and substitute once. Never chain substitutions by swapping a chosen stand-in for another. To change the stand-in, go back to the original message and pick another candidate.
- If the stand-in is more abstract than the noun in the original request, drop the substitution and use the original noun. Substitution turns what cannot be drawn into something that can. Going more abstract makes the picture harder to read.
- Choose by the message. A rising-trend graph request becomes something that embodies rising. Check that the usual impression of the stand-in fits the message before you offer it.
- For icons, choose an object with a silhouette that fills the frame. Skip landscapes made only of air and terrain, and subjects defined by material.
- Among several candidates, pick the one with the simplest, most familiar outline. Simple, common subjects give stable results.
- Convey direction and state by choosing a subject that carries that meaning itself. Phrases such as "rising" or "collapsing" rarely come through.
- More elements mean more omissions and misplacements, so keep elements few. Exact counts do not come through, so never make a count the message.
- Keep the subject description short. Limit mood words to color and time of day.
- For subjects outside the tables below, try at least two seeds before judging whether the style comes through.

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

Present the limits, the substitute, the output, and a request for confirmation in one message. Generate after the user agrees.

- Limits: drawn as requested, the diagram's text and connectors would carry no meaning. Numbers and ratios come through only as up and down, more and less.
- Substitute: sum up the core message of the original request in one sentence and offer one stand-in that fits it. Example: the core message of a three-stage growth roadmap is "we climb step by step".
- Output: the result is an icon or a scene of the stand-in.
- Text: if text and numbers are needed, keep the image as a background and add text on top in an editing tool.

Example:

> Diffusion models cannot draw text or precise line structures. I can turn your [original request] into a picture of [stand-in] that carries [core message]. You can add the text on top of the finished picture in an editing tool. Shall I go ahead?

- If the user agrees, generate with the substitute prompt. From there it is a normal request.
- If the user declines, pick another stand-in from the original message and offer it.

## Scene building

Scenes come out most stable with two or three common elements plus a time of day and a color. Diffusion models reproduce scene types they saw often in training.

- Elements: choose common ones such as sky, sea, mountains, a road, trees, a river, a forest, a city, a village, an industrial area, a lab, an office. Four or more elements bring more omissions and misplacements.
- Replace elements that point to a specific company or product with common ones. Specific products rarely come out right.
- Time of day: pick one of dawn, sunrise, noon, sunset, or night to fix the light direction and contrast.
- Color: pick one color family to match the palette of where it will be used.
- Example: a river and a city skyline at sunset with a warm orange family. Prompt: `city skyline beside a river at sunset, warm orange palette, wide horizon, watercolor illustration`
- To fit a full-body person into a wide banner, place the person in the distance or use an upper-body framing.
