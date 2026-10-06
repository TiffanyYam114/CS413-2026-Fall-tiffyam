# CS413-2026-Fall
For teaching (Agentic) Software Engineering

## Course website (Cloudflare Pages)

The `public/` directory is a standalone static website. Edit `public/index.html`
for course content and `public/styles.css` for styling. No build or dependencies
are needed. Course materials link to this repository on GitHub.

Preview locally from the repository root:

```sh
python3 -m http.server 8000 --directory public
```

Open http://localhost:8000.

To deploy with Cloudflare Pages, push these files to GitHub, then create a
**Pages** project under **Workers & Pages** in the Cloudflare dashboard and
connect this repository. Use these build settings:

| Setting | Value |
| --- | --- |
| Production branch | `main` |
| Framework preset | None |
| Build command | `exit 0` |
| Build output directory | `public` |
| Root directory | Leave blank (repository root) |

Deploy the project. Cloudflare provides a `*.pages.dev` address and redeploys
when you push to `main`. To use your own domain, add it in the Pages project's
**Custom domains** tab and follow the DNS instructions.

Alternatively, create a Pages **Direct Upload** project and upload the `public`
folder using the dashboard. Choose Git integration initially if you want
automatic deployments; a Direct Upload project cannot later switch to Git integration.

Publish only `public/`; the rest of the repository is not website output.
See the [Cloudflare static HTML guide](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/).

## Mirroring this repository

Please create a private repository that mirrors this one and update
frequently.

Step 1:

Please clone the class repository:

```
git clone https://github.com/hwxi/CS413-2026-Fall
```

Step 2:

Please create a repository of your own.
For instance, the following one is created
for my own use:

https://github.com/githwxi/CS413-2026-Fall-hwxi

Then please mirror-push the class repo into your own repo:

```
cd CS413-2026-Fall
git push --mirror https://github.com/githwxi/CS413-2026-Fall-hwxi
git clone https://github.com/githwxi/CS413-2026-Fall-hwxi
cd CS413-2026-Fall-hwxi
git remote add upstream https://hwxi@github.com/hwxi/CS413-2026-Fall.git
```

Step 3:

Please remember to sync with the class repo *frequently*:

```
git fetch upstream
git merge upstream/main main
```

Codex followed the initial prompt well and translated the source code into Python-3 
quite accurately. Some of the ATS functions, like `board_set` `search`, were 
difficult to understand, but the AI seemed to handle them pretty well. It also used 
a different approach than the ATS code to implement the `search` function because 
Python does not optimize tail recursion, which I would not have known.

There were some errors I found in the AI code, such as it not implementing 
`int8 = tuple[int, int, int, int, int, int, int, int]`. You could say this was a 
major error, since the original code uses this type a lot, but Codex's code replaced 
every instance of the `int8` type with `tuple[int, int, int, int, int, int, int, int]`, 
so there was practically no difference. The code was a bit longer, but it still worked. 

Additionally, in the `board_get` function, it translated an if-elif-else statement 
into only if statements, but that would not have affected the functionality. 

Since these errors were minor and did not affect the overall accurateness of the 
program, I believe the AI-generated code could have been trusted without testing. 
However, that's because it was given already written, specific code to translate. 
If we had just told the AI to write Python-3 code to solve the eight-queens problem, 
it may not have been completely correct, or the code may have been unnecessarily long.

Having AI translate the code for me decreased the amount of work I had to do by a lot. 
It would take me a while to understand the ATS code, then translate it into Python. 
I do have to review the AI code, but I am more familiar with Python than ATS. 
Having the AI write Python code for me to review and find errors is a lot easier than 
translating the code myself.
