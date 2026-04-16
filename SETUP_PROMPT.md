# Setup Prompt

Once you've cloned the repo, copy and paste the prompt below into Claude, ChatGPT, or any
AI assistant. It will walk you through hosting, configuring, and installing the apps on your R1.

---

```
I've just cloned the rabbit-r1-creations-public repo from GitHub. It contains a collection 
of custom apps (creations) for the Rabbit R1 device. I need your help getting them set up 
so I can install them on my R1.

Here's what needs doing:

1. **Choose which apps to set up** — the repo contains:
   - shopping-list (voice-powered shopping list)
   - todo (voice todo with 3 lists)
   - rep-tracker (daily exercise tracker with graphs)
   - rep-timer (workout interval timer)
   - spirit-level (bubble level using the accelerometer)
   - dice-roller (shake to roll, d4–d20)
   - notes (voice or keyboard notes with QR export)
   - r1-buddy (Tamagotchi-style companion)
   - gemma-chat (AI chat — requires your own backend, see step 6)
   Ask me which ones I want to set up.

2. **Host the apps** — each app is a plain HTML file that needs to be hosted at a public URL. 
   The easiest free option is Netlify (drag and drop the folder at netlify.com). 
   Ask me where I want to host them and help me through it if needed.

   Note: if you just want to use the pre-hosted versions of the standard apps (everything 
   except gemma-chat), you can skip hosting — the install pages already point to 
   https://andr3w-hilton.github.io/rabbit-r1-creations-public/ and the QR codes will 
   work as-is.

3. **Update the install URL** — if you're self-hosting, open each app's install.html and 
   replace the existing URL with your own hosted URL. For example:
   `https://mysite.netlify.app/shopping-list/`
   
   If you're using the pre-hosted GitHub Pages version, skip this step.

4. **Generate the install QR** — open the install.html in a browser. It will automatically 
   generate a QR code pointing to the app URL.

5. **Scan and install on the R1** — open the R1 camera, point at the QR code, and install.

6. **For gemma-chat only** — this app needs a backend server to proxy requests to an LLM.
   The repo includes web-server.py which handles this. You'll need:
   - A server to run it on (a cheap VPS, Railway, Fly.io, etc.)
   - A Google AI Studio API key (free tier available at aistudio.google.com)
   Set your API key as the GOOGLE_AI_API_KEY environment variable, then run web-server.py.
   Once running, open gemma-chat/index.html and replace `YOUR_GEMMA_PROXY_URL` with your 
   server's URL. Then update install.html with your hosted gemma-chat URL and scan the QR.

Important context about the R1:
- The R1 is a small AI device with a 240x282px screen
- Apps load from a URL every time they're opened — they need to stay hosted
- The side button = push to talk for voice input
- The scroll wheel navigates lists
- Long press the side button = voice recording in apps that support it
- All data is stored locally on the device (localStorage) — nothing is sent anywhere

Please start by asking me which apps I'd like to set up.
```
