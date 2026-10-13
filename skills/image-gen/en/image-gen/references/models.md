# Presets, precision, time estimates, the precise preset, and the cache

Details for the preset and environment check sections of SKILL.md. Read this when choosing a preset, working out time estimates, running the precise preset, or cleaning up the cache.

## Preset settings

Steps, guidance, and scheduler are fixed in the scripts. Many other combinations produce mushy shapes, so keep the defaults.

| Preset | Model repository | Scheduler | Steps | Guidance | Generation size | Basis |
|---|---|---|---|---|---|---|
| `dreamshaper-8-lcm` | Lykon/dreamshaper-8-lcm | LCM | 3 | 1.5 | 512x512 | Tuned to cut CPU time |
| `sdxs` | IDKiro/sdxs-512-dreamshaper | Model default | 1 | 0 | 512x512 | Set by the model card |
| `tiny-sd` | segmind/tiny-sd | DPM-Solver | 16 | 7.5 | 384x384 | Tuned for stable shapes |

- The model card example for `dreamshaper-8-lcm` uses 15 steps and guidance 2. LCM models are distilled to converge in few steps, so 3 steps still form shapes. The skill uses 3 steps to save CPU time.
- `sdxs` is a one-step model distilled with `dreamshaper-8-lcm` as its teacher. Its model card requires 1 step and guidance 0.
- `tiny-sd` turns mushy with the LCM scheduler and stays stable with DPM-Solver.
- Guidance above 1 runs the model twice per step, which adds time.

### How each preset behaves

- Standard (`dreamshaper-8-lcm`): dense detail in photographic texture, shallow depth of field, and watercolor bleed. It covers photographic, illustration, and watercolor styles depending on the style keywords. Abstract style phrases such as `minimal editorial style` can drift into portrait photos, and a technique name such as `watercolor illustration` brings the scene back. Flat vector keywords make shapes go mushy and then fall apart. Full-body people often come out with mismatched clothing on the left and right or mushy hands, and square full-body frames often cut off the feet.
- Light (`sdxs`): the fastest, and it tends to place scene elements as instructed. Detail is simpler than Standard. It tends to look like a digital painting even when asked for a photographic style. Flat requests come out semi-flat with leftover shading. The same person can appear twice, and props nobody asked for can show up.
- Flat (`tiny-sd`): better than the other presets at flat vector with solid fills and crisp edges, and at paint bleed with paper margins. Its shapes are less stable than Light's, and the subject can look detached from the background. It sometimes adds a cropped picture frame, and with people it often cuts the head off at the top. For watercolor that needs stable shapes, use Standard with `watercolor illustration`.
- If Flat drops the subject, try one more seed. If it is still missing, offer the user an alternative: Light with `flat vector art, solid flat colors, no shading`. Change the preset only with permission.
- Flat's weights are distributed as PyTorch pickle files (.bin). diffusers and transformers load them in weights-only mode.

## Precision

Generation and region redrawing load the model in float32 or bfloat16. The scripts choose in this order.

1. If the CPU has native bfloat16 instructions (AVX512_BF16 or AMX on x86), use bfloat16. It is faster and uses less memory.
2. Otherwise, if total memory meets the preset's float32 threshold, use float32.
3. Otherwise use bfloat16. It fits in memory, but the CPU emulates the instructions, so it runs several times slower. Tell the user it will be slower.

The instructions that process bfloat16 in hardware are part of AVX512_BF16 and AMX. On CPUs without them, bfloat16 matrix multiplication is broken down into other instructions and ends up slower than float32. `cpu.native_bf16` in probe.py holds this test. You can also force a choice with `--dtype fp32` or `--dtype bf16`.

| Target | float32 threshold (total memory) | bfloat16 threshold (total memory) |
|---|---|---|
| `dreamshaper-8-lcm` | 6.0GB | 3.5GB |
| `sdxs` | 3.5GB | 2.5GB |
| `tiny-sd` | 4.0GB | 3.0GB |
| Region redrawing | 6.0GB | 3.5GB |

Each threshold is the float32 weight file size plus working memory during generation. If total memory is below the bfloat16 threshold, generate.py stops with exit code 6.

## Time estimates

`probe.py --estimate` computes seconds per image from two values.

- Benchmark: it repeats a 1024x1024 matrix multiply for about 1.5 seconds and measures throughput (GFLOPS) in float32 and bfloat16, using all logical cores.
- Workload: the effective computation (GFLOP) a preset needs for one image. It was measured on a reference CPU as "real seconds per image x that CPU's benchmark GFLOPS" and stored in `WORK_GFLOP_PER_IMAGE` in probe.py.
- Estimated seconds = workload / the runtime environment's benchmark GFLOPS, using the same precision generate.py will pick.

Most of the work is matrix multiplication, so the ratio holds in rough terms, but memory speed, cache size, load from other programs, and heat shift it. Always call it an estimate, and report the real time after the first image.

- The first run adds model loading and download time. Loading takes from a few seconds to tens of seconds.
- To recalibrate a workload, multiply the GFLOPS from `probe.py --estimate` by the real `seconds` of one image in the same runtime environment and replace that entry.

## Precise preset (FLUX.2 klein 4B)

This runs a 4-billion-parameter model with a prebuilt stable-diffusion.cpp executable and 4-bit quantized files, with no compiling. It follows instructions and draws bodies with fewer errors than the SD 1.5 family, and it is the slowest.

- Executable: one pinned stable-diffusion.cpp release, checked by SHA-256. Only the Linux x86_64 build is pinned, so leave this preset out of the choices on other operating systems.
- Model files: the diffusion model (FLUX.2 klein 4B as GGUF Q4_0), the text encoder (Qwen3 4B as GGUF Q4_K_M), and the VAE (from the official FLUX.2 klein 4B repository), each fetched from its official publisher at a pinned revision. About 5.2GB in total.
- Settings: 4 steps, cfg 1.0 (the upstream example values), memory mapping (`--mmap`), and tiled VAE decoding are fixed. Without memory mapping the weights get copied into RAM and small machines run out of memory.
- Size: 384x512 by default, 512x704 pixels at most. Step time grows with pixel count, so reach larger sizes with final upscaling.
- Prompt: takes natural sentences as they are. No 77-token limit, no negative prompt.
- If the result is filled with a single color, it stops with exit code 7. Files quantized in other layouts can produce white images without any error, so use only the pinned files.
- Make one image per run. Report the estimate from `probe.py --estimate` before starting.

A run takes long, so start it in the background and follow the log. If the agent environment can be reset between conversation turns, finish the run and the wait within the same turn.

```
setsid nohup PY scripts/generate_klein.py "an adult woman in a black coat standing on a city street at night, photorealistic, framed from head to thighs" ./outputs/klein.png --seed 42 > ./outputs/klein.log 2>&1 < /dev/null &
```

- Watch the progress marks in the log (`1/4` through `4/4`), the output file, and the JSON on the last line.
- Never run it alongside another generation process. Together they run out of memory and get killed.

## Cache

Everything the skill downloads sits under the cache folder (`~/.cache/image-gen`, movable with `IMAGE_GEN_HOME`). Models go into a Hugging Face cache of the skill's own (`hf`) inside that folder. It never mixes with the Hugging Face cache other tools use, so deleting it affects no other tool. A model that exists elsewhere gets downloaded once more.

| cache.py target | Deleted |
|---|---|
| `dreamshaper-8-lcm`, `sdxs`, `tiny-sd` | That model repository |
| `flux2-klein-4b` | The three model repositories of the precise preset and the executable folder (`klein`) |
| `inpaint` | The region redrawing model and LCM-LoRA |
| `face` | The face restoration weight folder (`face`) |
| `sr` | The final upscaling weight folder (`sr`) |
| `all` | The whole cache folder except the virtual environment (`venv`) |

- The Hugging Face cache keeps real files in a shared store and only links in the model folders. Deleting a model folder frees no space, so delete through cache.py.
- Keep the default preset's cache while the conversation goes on. If disk runs short for the next download, delete caches of the other presets first.
- A deleted model downloads again when used. Delete after a series of images is finished.
- To remove everything the skill installed, run `cache.py delete all` and then delete the virtual environment folder (`venv`). Delete the virtual environment only after the user confirms.
