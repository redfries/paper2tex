# 📋 Preparing Your Document for paper2tex

> **Read this before you start.** 5 minutes of prep saves hours of fixing.

---

## 📄 Step 1: Is Your File Ready?

### Your file MUST be `.docx`

```
✅  paper.docx          ← This works
✅  thesis_draft.docx   ← This works
✅  my paper v3.docx    ← This works (spaces in name are fine)

❌  paper.doc            ← Old format. Open in Word → Save As → .docx
❌  paper.pdf            ← Not a Word file. We can't use this.
❌  paper.rtf            ← Open in Word → Save As → .docx
❌  Google Docs link     ← Go to File → Download → Microsoft Word (.docx)
```

> **Using Google Docs?** Just click `File → Download → Microsoft Word (.docx)` and use that file.

---

## ✍️ Step 2: Check Your Headings

### Use Word's built-in heading styles — don't just make text bold

This is the **#1 mistake** students make. The tool finds your sections by looking for heading styles, not bold text.

```
✅ RIGHT WAY (uses Heading styles):

   ┌──────────────────────────────┐
   │  Introduction      [Heading 1]│  ← Selected "Heading 1" from the ribbon
   │  Related Work      [Heading 1]│
   │  Our Approach      [Heading 1]│
   │    Data Collection [Heading 2]│  ← "Heading 2" for subsections
   │    Model Design    [Heading 2]│
   │  Results           [Heading 1]│
   │  Conclusion        [Heading 1]│
   │  References        [Heading 1]│
   └──────────────────────────────┘


❌ WRONG WAY (just bold text):

   ┌──────────────────────────────┐
   │  **Introduction**   [Normal] │  ← Looks like a heading but isn't one
   │  **Related Work**   [Normal] │     The tool can't tell this apart from
   │  **Our Approach**   [Normal] │     regular bold text in a paragraph
   └──────────────────────────────┘
```

**How to fix it:** Select your heading text → go to the **Home** tab → click **Heading 1** (or Heading 2 for subsections) in the Styles group.

---

## 🔢 Step 3: Check Your Equations

### Use Word's equation editor — not images or MathType

```
✅ WORKS PERFECTLY:
   Word's built-in equation editor (Insert → Equation)
   These are stored as "OMML" — we convert them perfectly to LaTeX.

⚠️ WORKS WITH WARNINGS:
   MathType equations (old plugin)
   We'll detect them and tell you which ones need to be re-entered.

❌ DOES NOT WORK:
   Screenshots of equations pasted as images
   We'll treat them as figures, not math — you'll need to re-type them.
```

> **Quick test:** Click on one of your equations. If a blue "Equation" box appears around it, you're good ✅. If it just selects like a picture, it's an image ❌.

---

## 📊 Step 4: Check Your Tables

### Regular Word tables work — even complex ones

```
✅ Normal Word tables                    → Works perfectly
✅ Tables with merged cells              → We handle this (multicolumn/multirow)
✅ Tables with numbers, text, symbols    → All preserved
✅ Tables with bold headers              → Auto-detected

⚠️ Tables drawn with text art / tab stops → Won't be recognized as a table
```

> **Quick test:** Click inside your table. If you see the "Table Design" tab appear in the ribbon, it's a real Word table ✅.

---

## 🖼️ Step 5: Prepare Your Figures

### You have two options — both work

**Option A: Figures are inside the Word document**
```
✅ This works. We extract them automatically.
⚠️ Quality may be lower (Word sometimes compresses images).
```

**Option B: Figures are in a separate folder (RECOMMENDED)**
```
✅ Put your original, high-quality figures in a folder next to your .docx:

   my_paper/
   ├── paper.docx
   └── figures/          ← We auto-detect this folder
       ├── fig1.png
       ├── fig2.pdf      ← PDF/SVG = best quality (vector graphics)
       └── fig3.jpg
```

We automatically scan these folder names: `figures/`, `figs/`, `images/`, `img/`, `pics/`, `media/`, `plots/`

> **Pro tip:** If you have graphs or diagrams, export them as **PDF** from your plotting tool (matplotlib, Excel, etc.). PDF figures look much sharper in the final paper than PNG/JPG.

---

## 📚 Step 6: Check Your References

### Any of these formats work — listed from best to okay

```
🥇 BEST: Zotero, Mendeley, or EndNote citations
   → We extract perfect BibTeX directly from the hidden data in your .docx
   → Zero errors guaranteed

🥈 GOOD: A "References" section with numbered entries [1], [2], [3]
   → We parse each reference and verify it online
   → Example:
     References
     [1] Smith, J. "Deep Learning for NLP." ICML, 2024.
     [2] Lee, C. et al. "Transformer architectures." NeurIPS, 2023.

🥉 OKAY: A "References" section with author-year citations (Smith, 2024)
   → We can handle this but it's harder to parse automatically

❌ BAD: References scattered throughout the document with no clear section
   → We might miss some. Put them all under a "References" heading.
```

---

## 🎯 Step 7: Tell the Agent What You Need

### What to say

Pick one and tell your AI agent:

```
Simple:
  "Convert my paper.docx to IEEE conference format"

With figures:
  "Convert paper.docx to ACM SIGCONF. My figures are in the figs/ folder."

With template file:
  "Convert paper.docx for NeurIPS 2026. Use this template: neurips_2026.zip"
```

### Supported conferences (built-in — no template file needed)

| Just say... | Template used |
|-------------|--------------|
| "IEEE conference" | IEEEtran (conference mode) |
| "IEEE journal" or "IEEE transactions" | IEEEtran (journal mode) |
| "ACM" or "ACM SIGCONF" | acmart (sigconf) |
| "Springer LNCS" | llncs |
| "NeurIPS" | neurips |
| "ICML" | icml |
| "CVPR" | cvpr |

**Other conferences:** Provide the template `.zip` file that you downloaded from the conference website.

---

## 📂 The Ideal Setup

If you follow all the steps above, your folder should look something like this:

```
my_paper/
├── paper.docx              ← Your Word document
├── figures/                 ← Your high-quality figures (optional)
│   ├── architecture.pdf
│   ├── results.png
│   └── comparison.svg
└── template.zip             ← Conference template (optional for built-in ones)
```

Then just tell your agent: **"Convert paper.docx to \<conference\> format"** and let it work.

---

## ❓ Common Questions

**"I wrote my paper in Google Docs, not Word"**
→ Go to File → Download → Microsoft Word (.docx). Use that file.

**"My equations are images I pasted from a textbook"**
→ You'll need to re-type them using Word's equation editor (Insert → Equation). The tool can't read images of math.

**"I have 50 figures in different folders"**
→ Put them all in one `figures/` folder next to your `.docx`. Or tell the agent: "my figures are in `path/to/my/figures/`"

**"My paper is in LaTeX already"**
→ You don't need this tool! You're already in the right format. Just apply the conference template directly.

**"Can I use .doc (the old format)?"**
→ No. Open it in Word and do File → Save As → Word Document (.docx).

**"I used MathType for my equations"**
→ The tool will detect them and warn you. You'll need to re-enter those specific equations using Word's built-in editor. Most equations added after Word 2016 already use the built-in editor.

**"My references aren't numbered, they're like (Author, Year)"**
→ That works too. Just make sure they're all under a "References" heading.
