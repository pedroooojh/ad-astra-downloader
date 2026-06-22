_SHARED = """
    QWidget {
        font-family: "Space Grotesk", "Inter", "Segoe UI", sans-serif;
        font-size: 12px;
        font-weight: 400;
    }
    QLabel { background: transparent; }
    #mainCard { background: transparent; border: 0; }
    #videoTitle { font-size: 13px; font-weight: 600; }
    #tagline {
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        font-size: 10px; font-weight: 500; letter-spacing: 3px;
    }
    #footer {
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        font-size: 9px; letter-spacing: 2px;
    }
    #secondary {
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        font-size: 11px;
    }
    #optionsHint, #downloadHint {
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        font-size: 11px; letter-spacing: 1px;
    }
    #sectionLabel {
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        font-size: 10px; font-weight: 500; letter-spacing: 3px;
    }
    #urlError {
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        color: #ff4444; font-size: 10px; letter-spacing: 1px;
    }
    QLineEdit {
        border: 0; border-radius: 0; padding: 8px 0; font-size: 13px;
        background: transparent;
    }
    #destinationInput {
        background: transparent; border: 0; padding: 0;
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        font-size: 12px;
    }
    #destinationInput:focus { border: 0; }
    QPushButton {
        border-radius: 3px; padding: 7px 13px;
        font-size: 12px; font-weight: 500;
    }
    #platformChip {
        border: 0; border-radius: 0; background: transparent;
        padding: 4px 0; margin-right: 14px;
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        font-size: 10px; font-weight: 500; letter-spacing: 2px;
    }
    #analyzeButton {
        border: 0; border-radius: 0; background: transparent;
        padding: 4px 0;
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        font-size: 10px; font-weight: 700; letter-spacing: 2px;
        text-decoration: underline;
    }
    #segment { border-radius: 4px; }
    #segmentButton {
        border: 0; border-radius: 3px; padding: 7px;
        font-size: 12px; font-weight: 500;
    }
    #segmentButton:hover { background: transparent; border: 0; }
    #qualityPanel { background: transparent; }
    #formatChip {
        border-radius: 3px; padding: 5px 11px; font-size: 11px; font-weight: 500;
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
    }
    #destinationBox { border-radius: 3px; }
    #folderButton { border: 0; border-radius: 0; padding: 0; }
    #downloadButton { border: 0; border-radius: 3px; font-size: 14px; font-weight: 700; }
    #progressMeta {
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        font-size: 11px; letter-spacing: 1px;
    }
    QProgressBar { border: 0; border-radius: 2px; }
    QProgressBar::chunk { border-radius: 2px; }
    #errorText {
        font-family: "JetBrains Mono", "Space Mono", "Consolas", monospace;
        color: #ff4444; font-size: 11px;
    }
    #linkButton { border: 0; padding: 2px; text-decoration: underline; }
    #themeToggle { border-radius: 13px; padding: 0; font-size: 13px; }
"""

DARK_STYLESHEET = _SHARED + """
    /* AD ASTRA dark — #050505 bg, #f0f0f0 text */
    QWidget { background: #050505; color: #f0f0f0; }
    #root { background: #050505; }
    #logo { background: transparent; }
    #tagline { color: rgba(255,255,255,100); }
    #footer { color: rgba(255,255,255,45); }
    #secondary { color: rgba(255,255,255,100); }
    #resultCard #secondary { color: rgba(255,255,255,75); }
    #optionsHint, #downloadHint { color: rgba(255,255,255,60); }
    #sectionLabel { color: rgba(255,255,255,75); }
    #videoTitle { color: #f0f0f0; }
    #resultCard {
        background: #0a0a0a; border: 1px solid rgba(255,255,255,20); border-radius: 4px;
    }
    #thumbnail {
        background: #0d0d0d; border: 1px solid rgba(255,255,255,15);
        border-radius: 3px; color: rgba(255,255,255,45);
    }
    QLineEdit {
        color: #f0f0f0;
        placeholder-text-color: rgba(255,255,255,30);
        selection-background-color: #f0f0f0; selection-color: #050505;
    }
    QLineEdit#urlInput {
        border-bottom: 1px solid rgba(255,255,255,22);
    }
    QLineEdit#urlInput:focus { border-bottom-color: rgba(255,255,255,80); }
    QLineEdit#urlInput[urlState="valid"] { border-bottom-color: rgba(255,255,255,80); }
    QLineEdit#urlInput[urlState="invalid"] { border-bottom-color: #ff4444; }
    QPushButton {
        background: transparent; border: 1px solid rgba(255,255,255,28);
        color: rgba(255,255,255,153);
    }
    QPushButton:hover { border-color: rgba(255,255,255,89); color: #f0f0f0; }
    QPushButton:focus { border-color: rgba(255,255,255,89); }
    #platformChip { color: rgba(255,255,255,38); }
    #platformChip:hover { color: rgba(255,255,255,100); }
    #platformChip[active="true"] { color: rgba(255,255,255,160); border-bottom: 1px solid rgba(255,255,255,55); }
    #platformChip[active="false"] { color: rgba(255,255,255,38); border-bottom: 1px solid transparent; }
    #analyzeButton { color: rgba(255,255,255,100); }
    #analyzeButton:hover { color: #f0f0f0; }
    #analyzeButton:disabled { color: rgba(255,255,255,22); text-decoration: none; }
    #segment { background: #0a0a0a; border: 1px solid rgba(255,255,255,15); }
    #segmentButton { color: rgba(255,255,255,102); }
    #segmentButton:hover { color: #f0f0f0; }
    #segmentButton[active="true"]  { background: #f0f0f0; color: #050505; }
    #segmentButton[active="false"] { background: transparent; color: rgba(255,255,255,102); }
    #segmentButton[active="true"]:hover { background: #f0f0f0; color: #050505; }
    #formatChip {
        background: transparent; border: 1px solid rgba(255,255,255,22);
        color: rgba(255,255,255,102);
    }
    #formatChip:hover { border-color: rgba(255,255,255,89); color: #f0f0f0; }
    #formatChip[active="true"]  { background: #f0f0f0; color: #050505; border-color: #f0f0f0; }
    #formatChip[active="false"] { background: transparent; color: rgba(255,255,255,102); }
    #formatChip[active="true"]:hover { background: #f0f0f0; color: #050505; border-color: #f0f0f0; }
    #destinationBox { background: #0a0a0a; border: 1px solid rgba(255,255,255,22); }
    #destinationInput { color: rgba(255,255,255,102); }
    #folderButton { border-left: 1px solid rgba(255,255,255,15); }
    #folderButton:hover { border-left-color: rgba(255,255,255,89); }
    #downloadButton { background: #f0f0f0; color: #050505; }
    #downloadButton:hover { background: #ffffff; color: #050505; }
    #downloadButton:disabled {
        background: rgba(255,255,255,12); color: rgba(255,255,255,35);
    }
    #progressMeta { color: rgba(255,255,255,100); }
    QProgressBar { background: rgba(255,255,255,12); }
    QProgressBar::chunk { background: #f0f0f0; }
    #completionText { color: #f0f0f0; }
    #linkButton { color: rgba(255,255,255,153); }
    #linkButton:hover { color: #f0f0f0; }
    #themeToggle { border: 1px solid rgba(255,255,255,22); color: rgba(255,255,255,80); }
    #themeToggle:hover { border-color: rgba(255,255,255,89); color: #f0f0f0; }
"""

LIGHT_STYLESHEET = _SHARED + """
    /* AD ASTRA light — #fafafa bg, #0a0a0a text */
    QWidget { background: #fafafa; color: #0a0a0a; }
    #root { background: #fafafa; }
    #logo { background: transparent; }
    #tagline { color: rgba(0,0,0,100); }
    #footer { color: rgba(0,0,0,45); }
    #secondary { color: rgba(0,0,0,100); }
    #resultCard #secondary { color: rgba(0,0,0,75); }
    #optionsHint, #downloadHint { color: rgba(0,0,0,60); }
    #sectionLabel { color: rgba(0,0,0,75); }
    #videoTitle { color: #0a0a0a; }
    #resultCard {
        background: #f2f2f2; border: 1px solid rgba(0,0,0,20); border-radius: 4px;
    }
    #thumbnail {
        background: #e8e8e8; border: 1px solid rgba(0,0,0,15);
        border-radius: 3px; color: rgba(0,0,0,45);
    }
    QLineEdit {
        color: #0a0a0a;
        placeholder-text-color: rgba(0,0,0,30);
        selection-background-color: #0a0a0a; selection-color: #fafafa;
    }
    QLineEdit#urlInput {
        border-bottom: 1px solid rgba(0,0,0,22);
    }
    QLineEdit#urlInput:focus { border-bottom-color: rgba(0,0,0,80); }
    QLineEdit#urlInput[urlState="valid"] { border-bottom-color: rgba(0,0,0,80); }
    QLineEdit#urlInput[urlState="invalid"] { border-bottom-color: #ff4444; }
    QPushButton {
        background: transparent; border: 1px solid rgba(0,0,0,28);
        color: rgba(0,0,0,153);
    }
    QPushButton:hover { border-color: rgba(0,0,0,89); color: #0a0a0a; }
    QPushButton:focus { border-color: rgba(0,0,0,89); }
    #platformChip { color: rgba(0,0,0,38); }
    #platformChip:hover { color: rgba(0,0,0,100); }
    #platformChip[active="true"] { color: rgba(0,0,0,160); border-bottom: 1px solid rgba(0,0,0,55); }
    #platformChip[active="false"] { color: rgba(0,0,0,38); border-bottom: 1px solid transparent; }
    #analyzeButton { color: rgba(0,0,0,100); }
    #analyzeButton:hover { color: #0a0a0a; }
    #analyzeButton:disabled { color: rgba(0,0,0,22); text-decoration: none; }
    #segment { background: #f2f2f2; border: 1px solid rgba(0,0,0,15); }
    #segmentButton { color: rgba(0,0,0,102); }
    #segmentButton:hover { color: #0a0a0a; }
    #segmentButton[active="true"]  { background: #0a0a0a; color: #fafafa; }
    #segmentButton[active="false"] { background: transparent; color: rgba(0,0,0,102); }
    #segmentButton[active="true"]:hover { background: #0a0a0a; color: #fafafa; }
    #formatChip {
        background: transparent; border: 1px solid rgba(0,0,0,22);
        color: rgba(0,0,0,102);
    }
    #formatChip:hover { border-color: rgba(0,0,0,89); color: #0a0a0a; }
    #formatChip[active="true"]  { background: #0a0a0a; color: #fafafa; border-color: #0a0a0a; }
    #formatChip[active="false"] { background: transparent; color: rgba(0,0,0,102); }
    #formatChip[active="true"]:hover { background: #0a0a0a; color: #fafafa; border-color: #0a0a0a; }
    #destinationBox { background: #f2f2f2; border: 1px solid rgba(0,0,0,22); }
    #destinationInput { color: rgba(0,0,0,102); }
    #folderButton { border-left: 1px solid rgba(0,0,0,15); }
    #folderButton:hover { border-left-color: rgba(0,0,0,89); }
    #downloadButton { background: #0a0a0a; color: #fafafa; }
    #downloadButton:hover { background: #1a1a1a; color: #ffffff; }
    #downloadButton:disabled {
        background: rgba(0,0,0,12); color: rgba(0,0,0,35);
    }
    #progressMeta { color: rgba(0,0,0,100); }
    QProgressBar { background: rgba(0,0,0,12); }
    QProgressBar::chunk { background: #0a0a0a; }
    #completionText { color: #0a0a0a; }
    #linkButton { color: rgba(0,0,0,153); }
    #linkButton:hover { color: #0a0a0a; }
    #themeToggle { border: 1px solid rgba(0,0,0,22); color: rgba(0,0,0,80); }
    #themeToggle:hover { border-color: rgba(0,0,0,89); color: #0a0a0a; }
"""
