APP_QSS = """
* { font-family: "Malgun Gothic", "Segoe UI", sans-serif; color: #0F172A; }

QMainWindow, QWidget#Stage { background: #F4F5F7; }

/* ── Window / Layout ── */
QFrame#Window { background: #FFFFFF; border: 0; }
QFrame#Sidebar {
    background: #F8F9FB;
    border-right: 1px solid #E4E7EC;
}
QFrame#Main { background: #FFFFFF; }
QFrame#Header {
    background: #FFFFFF;
    border-bottom: 1px solid #EDF0F3;
}

/* ── Typography ── */
QLabel#AppName  { font-size: 14px; font-weight: 700; letter-spacing: -0.3px; }
QLabel#AppDesc  { font-size: 11px; color: #94A3B8; }
QLabel#Title    { font-size: 20px; font-weight: 700; letter-spacing: -0.5px; }
QLabel#Subtitle { font-size: 12px; color: #94A3B8; }
QLabel#SectionTitle {
    font-size: 11px; font-weight: 600; color: #94A3B8;
    text-transform: uppercase; letter-spacing: 1px;
}
QLabel#CountBadge {
    font-size: 11px; font-weight: 600; color: #475569;
    background: #F4F5F7; border-radius: 9px; padding: 1px 6px;
}

/* ── Sidebar logo ── */
QLabel#LogoBadge {
    background: #3B68F1;
    border-radius: 8px;
    color: white;
    font-size: 13px;
    font-weight: 800;
}
QLabel#DKAvatar {
    border-radius: 14px;
    color: white;
    font-size: 12px;
    font-weight: 700;
    background: #E11D48;
}

/* ── New Search button ── */
QFrame#NewSearchBtn {
    background: #FFFFFF;
    border: 1px solid #E4E7EC;
    border-radius: 8px;
}
QFrame#NewSearchBtn:hover { border-color: #D0D5DD; background: #FAFAFA; }
QLabel#BtnPlus { font-size: 16px; font-weight: 400; color: #475569; }
QLabel#BtnText { font-size: 13px; font-weight: 500; }
QLabel#KbdKey {
    font-size: 10px; color: #475569;
    background: #F4F5F7; border: 1px solid #E4E7EC;
    border-radius: 3px; padding: 0 3px;
    font-family: "Consolas";
}

/* ── Sidebar items ── */
QFrame#SideItem {
    border-radius: 6px;
    background: transparent;
}
QFrame#SideItem:hover { background: #EEF0F3; }
QFrame#SideItemActive {
    border-radius: 6px;
    background: #EEF4FF;
}
QLabel#SideLabel  { font-size: 13px; color: #475569; }
QLabel#SideLabelActive { font-size: 13px; font-weight: 500; color: #1E3FAF; }
QLabel#SideFavLabel { font-size: 12px; color: #475569; font-family: "Consolas"; }
QLabel#SideMeta  { font-size: 11px; color: #94A3B8; }

/* ── Sidebar footer ── */
QFrame#SideFooter { border-top: 1px solid #E4E7EC; }
QLabel#FooterName { font-size: 12px; font-weight: 500; }
QLabel#FooterMeta { font-size: 11px; color: #94A3B8; }
QLabel#ChatFormLabel { color: #64748B; font-size: 11px; font-weight: 700; }

/* ── Buttons ── */
QPushButton {
    background: #FFFFFF; border: 1px solid #E4E7EC;
    border-radius: 7px; padding: 0 12px;
    font-size: 13px; font-weight: 500;
    height: 32px;
}
QPushButton:hover { background: #F4F5F7; border-color: #D0D5DD; }
QPushButton:pressed { background: #E6E9EF; }
QPushButton:disabled { color: #94A3B8; border-color: #E4E7EC; background: #F8FAFC; }
QPushButton#Primary {
    background: #3B68F1; border-color: #2952D6; color: white;
}
QPushButton#Primary:hover { background: #2952D6; }
QPushButton#Primary:disabled { opacity: 0.5; }
QPushButton#Ghost { border: 0; background: transparent; color: #475569; }
QPushButton#Ghost:hover { background: #F4F5F7; border: 1px solid #E4E7EC; }
QPushButton#ChatSideBtn {
    background: #FFFFFF; border: 1px solid #E4E7EC;
    border-radius: 8px; height: 34px;
    color: #1E3FAF; font-size: 13px; font-weight: 600;
    text-align: left; padding: 0 12px;
}
QPushButton#ChatSideBtn:hover { background: #EEF4FF; border-color: #D5E0FF; }
QPushButton#ChatSideBtnActive {
    background: #EEF4FF; border: 1px solid #D5E0FF;
    border-radius: 8px; height: 34px;
    color: #1E3FAF; font-size: 13px; font-weight: 800;
    text-align: left; padding: 0 12px;
}
QPushButton#DangerGhost { border: 0; background: transparent; color: #BE123C; }
QPushButton#DangerGhost:hover { background: #FEF2F2; border: 1px solid #FECDD3; }
QPushButton#IconBtn {
    border: 0; background: transparent; color: #94A3B8;
    border-radius: 6px; padding: 0; width: 26px; height: 26px;
}
QPushButton#IconBtn:hover { background: #F4F5F7; color: #0F172A; }
QPushButton#FavOn {
    border: 0; background: transparent; color: #F59E0B;
    border-radius: 6px; padding: 0; width: 26px; height: 26px;
    font-size: 15px;
}
QPushButton#FavOn:hover { background: #FFFBEB; }
QPushButton#FavOff {
    border: 0; background: transparent; color: #94A3B8;
    border-radius: 6px; padding: 0; width: 26px; height: 26px;
    font-size: 15px;
}
QPushButton#FavOff:hover { background: #F4F5F7; color: #0F172A; }

/* ── Tab buttons ── */
QFrame#TabBar {
    background: #F4F5F7; border: 1px solid #E4E7EC;
    border-radius: 8px; padding: 2px;
}
QPushButton#TabBtn {
    border: 0; background: transparent;
    color: #475569; font-size: 12px; font-weight: 500;
    border-radius: 6px; height: 28px; padding: 0 12px;
}
QPushButton#TabBtn:hover { color: #0F172A; }
QPushButton#TabBtnActive {
    border: 0; background: #FFFFFF; color: #0F172A;
    font-size: 12px; font-weight: 700;
    border-radius: 6px; height: 28px; padding: 0 12px;
}

/* ── Settings gear button ── */
QPushButton#GearBtn {
    border: 0; background: transparent; color: #94A3B8;
    border-radius: 6px; width: 26px; height: 26px; font-size: 15px;
}
QPushButton#GearBtn:hover { background: #E6E9EF; color: #475569; }

/* ── Input Panel ── */
QFrame#InputPanel {
    background: #FFFFFF; border: 1px solid #E4E7EC;
    border-radius: 12px;
}
QFrame#PanelTop {
    background: linear-gradient(to bottom, #FBFBFC, #F8F9FB);
    border-bottom: 1px solid #EDF0F3;
    border-top-left-radius: 12px; border-top-right-radius: 12px;
}
QLabel#PanelTagLabel {
    font-size: 11px; font-weight: 600; color: #475569;
    text-transform: uppercase; letter-spacing: 0.05em;
}
QLabel#PanelHelper { font-size: 12px; color: #94A3B8; }

/* ── Chip area ── */
QFrame#ChipArea {
    background: #FFFFFF;
    min-height: 110px;
}
QFrame#Chip {
    background: #EEF4FF; border: 1px solid #D5E0FF;
    border-radius: 14px;
}
QLabel#ChipText {
    color: #1E3FAF; font-family: "Consolas"; font-weight: 600;
    font-size: 13px; background: transparent;
}
QLabel#ChipQty {
    color: #1E3FAF; font-size: 11px; font-weight: 600;
    background: rgba(59,104,241,0.15); border-radius: 9px;
    padding: 0 4px; font-family: "Consolas";
}
QLineEdit#ChipQtyInput {
    color: #1E3FAF; font-size: 11px; font-weight: 600;
    background: rgba(59,104,241,0.10); border: 0;
    border-radius: 9px; padding: 0 4px; font-family: "Consolas";
}
QLineEdit#ChipQtyInput:hover {
    background: rgba(59,104,241,0.16);
}
QLineEdit#ChipQtyInput:focus {
    background: #FFFFFF;
    border: 1px solid #9DB6FF;
}
QFrame#Chip QPushButton {
    border: 0; background: transparent; color: #1E3FAF;
    border-radius: 10px; font-size: 14px; width: 20px; height: 20px;
    padding: 0;
}
QFrame#Chip QPushButton:hover { background: rgba(59,104,241,0.15); }
QLineEdit#ChipLineEdit {
    border: 0; background: transparent;
    font-size: 13px; font-family: "Consolas";
    color: #0F172A; padding: 4px 2px;
    selection-background-color: #D5E0FF;
}
QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #D0D5DD;
    border-radius: 8px;
    color: #0F172A;
    selection-background-color: #EEF4FF;
    selection-color: #1E3FAF;
    padding: 4px;
    outline: 0;
}

/* ── Options row ── */
QFrame#OptionsRow {
    background: #FCFCFD; border-top: 1px solid #EDF0F3;
    border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;
}
QLabel#OptLabel { font-size: 12px; color: #94A3B8; }
QLineEdit#NumInput {
    background: #FFFFFF; border: 1px solid #E4E7EC;
    border-radius: 6px; padding: 0 8px;
    font-size: 13px; font-family: "Consolas";
    text-align: right; height: 28px; width: 64px;
}
QLineEdit#NumInput:focus { border-color: #3B68F1; }

/* ── Filter bar ── */
QComboBox {
    background: #FFFFFF;
    border: 1px solid #E4E7EC;
    border-radius: 6px;
    padding: 0 24px 0 10px;
    font-size: 12px;
    font-weight: 500;
    color: #475569;
    height: 28px;
    min-width: 64px;
}
QComboBox:hover { background: #F4F5F7; border-color: #D0D5DD; }
QComboBox:focus { border-color: #3B68F1; }
QComboBox::drop-down {
    border: 0;
    border-left: 1px solid #E4E7EC;
    width: 22px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background: transparent;
}
QComboBox::drop-down:hover { background: #EEF0F3; }
QCheckBox#FilterCheck {
    font-size: 12px;
    color: #475569;
    spacing: 5px;
}
QCheckBox#FilterCheck::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #D0D5DD;
    border-radius: 3px;
    background: #FFFFFF;
}
QCheckBox#FilterCheck::indicator:hover { border-color: #3B68F1; }
QCheckBox#FilterCheck::indicator:checked {
    background: #3B68F1;
    border-color: #3B68F1;
}
QFrame#FilterSep {
    background: #E4E7EC;
    max-width: 1px;
    min-width: 1px;
}

QLineEdit {
    background: #FFFFFF; border: 1px solid #E4E7EC;
    border-radius: 7px; padding: 4px 7px;
}
QLineEdit:focus { border: 1px solid #3B68F1; }

/* ── Status strip ── */
QFrame#StripNeutral {
    background: #F4F5F7; border: 1px solid #E4E7EC; border-radius: 10px;
}
QFrame#StripSearching {
    background: #EEF4FF; border: 1px solid #D5E0FF; border-radius: 10px;
}
QFrame#StripSuccess {
    background: #ECFDF5; border: 1px solid #BBF7D0; border-radius: 10px;
}
QFrame#StripCancelled {
    background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 10px;
}
QFrame#StripError {
    background: #FEF2F2; border: 1px solid #FECDD3; border-radius: 10px;
}
QLabel#StripText { font-size: 13px; font-weight: 500; color: #047857; }
QLabel#StripTextBlue { font-size: 13px; font-weight: 500; color: #1E3FAF; }
QLabel#StripTextWarn { font-size: 13px; font-weight: 500; color: #B45309; }
QLabel#StripTextErr  { font-size: 13px; font-weight: 500; color: #BE123C; }
QLabel#StripMuted { font-size: 13px; color: #047857; opacity: 0.7; }
QLabel#StripDoneTag {
    font-size: 12px; font-weight: 600; color: #475569;
    background: transparent;
}
QProgressBar#StripBar {
    background: rgba(16,185,129,0.18); border: 0; border-radius: 2px;
    height: 4px; text-align: center;
}
QProgressBar#StripBar::chunk { background: #10B981; border-radius: 2px; }
QProgressBar#StripBarBlue {
    background: rgba(59,104,241,0.15); border: 0; border-radius: 2px;
    height: 4px;
}
QProgressBar#StripBarBlue::chunk { background: #3B68F1; border-radius: 2px; }

/* ── Category page ── */
QWidget#CategoryPage { background: #FFFFFF; }
QLabel#CategoryPageTitle { font-size: 16px; font-weight: 700; letter-spacing: -0.3px; }
QPushButton#CategoryBackBtn {
    background: #FFFFFF; border: 1px solid #D0D5DD; border-radius: 999px; height: 32px;
    color: #475569; font-size: 12px; font-weight: 700; padding: 0 12px;
}
QPushButton#CategoryBackBtn:hover { background: #F8FAFC; border-color: #98A2B3; }
QLabel#CategoryLastBadge {
    font-size: 11px; font-weight: 700; color: #1E3FAF;
    background: #EEF4FF; border: 1px solid #D5E0FF; border-radius: 999px;
    padding: 4px 9px; max-width: 180px;
}
QLabel#CategoryPageSub { font-size: 12px; color: #94A3B8; }
QFrame#CategoryHintCard {
    background: #F8FAFF; border: 1px solid #D5E0FF; border-radius: 12px;
}
QLabel#CategoryHintTitle { font-size: 12px; font-weight: 700; color: #1E3FAF; }
QLabel#CategoryHintBody { font-size: 12px; color: #475569; }
QFrame#CategoryTile {
    background: #FFFFFF; border: 1px solid #E4E7EC; border-radius: 10px;
    min-width: 90px; min-height: 90px;
}
QFrame#CategoryTile:hover { background: #EEF4FF; border-color: #D5E0FF; }
QLabel#TileIcon { font-size: 18px; color: #0F172A; background: transparent; }
QLabel#TileSymbol { background: transparent; }
QLabel#TileKo { font-size: 13px; font-weight: 600; color: #0F172A; background: transparent; }
QLabel#TileEn { font-size: 10px; color: #94A3B8; background: transparent; }
QPushButton#CategorySideBtn {
    background: #F8FAFF; border: 1px solid #D5E0FF; border-radius: 10px; height: 38px;
    color: #1E3FAF; font-size: 13px; font-weight: 700; text-align: left; padding: 0 12px;
}
QPushButton#CategorySideBtn:hover { background: #EEF4FF; border-color: #9DB6FF; }
QPushButton#CategorySideBtnActive {
    background: #E0EAFF; border: 1px solid #9DB6FF; border-radius: 10px; height: 38px;
    color: #16379A; font-size: 13px; font-weight: 800; text-align: left; padding: 0 12px;
}
QFrame#CategoryEmptyCard {
    background: #FFFFFF; border: 1px dashed #D0D5DD; border-radius: 12px;
}
QLabel#CategoryEmptyTitle { font-size: 14px; font-weight: 700; color: #0F172A; }
QLabel#CategoryEmptyBody { font-size: 12px; color: #667085; }

/* ── Results section ── */
QLabel#ResultsTitle { font-size: 14px; font-weight: 700; letter-spacing: -0.3px; }
QLabel#ResultCount {
    font-size: 11px; font-weight: 600; color: #475569;
    background: #F4F5F7; border-radius: 9px; padding: 2px 7px;
}

/* ── Result Card ── */
QFrame#Card {
    background: #FFFFFF; border: 1px solid #E4E7EC;
    border-radius: 12px;
}
QFrame#Card:hover { border-color: #D0D5DD; }
QFrame#CardStripeOk { background: #10B981; border-top-left-radius: 12px; border-top-right-radius: 12px; }
QFrame#CardStripeWarn { background: #F59E0B; border-top-left-radius: 12px; border-top-right-radius: 12px; }
QFrame#CardStripeError { background: #EF4444; border-top-left-radius: 12px; border-top-right-radius: 12px; }
QFrame#CardHead {
    background: #FFFFFF; border-bottom: 1px solid #EDF0F3;
    border-top-left-radius: 12px; border-top-right-radius: 12px;
}
QLabel#CardNumber {
    background: #F4F5F7; color: #94A3B8;
    border-radius: 7px; font-family: "Consolas";
    font-size: 11px; font-weight: 700;
}
QLabel#PartName {
    font-family: "Consolas"; font-size: 16px; font-weight: 700;
}
QLabel#OkBadge {
    background: #10B981; border-radius: 7px;
    color: white; font-size: 9px; font-weight: 700;
}
QLabel#CardMaker { font-size: 12px; color: #94A3B8; }
QLabel#CardMaker QLabel { color: #475569; font-weight: 500; }

/* KV grid */
QLabel#KvKey { font-size: 12px; color: #94A3B8; font-weight: 500; }
QLabel#KvVal { font-size: 12px; color: #0F172A; }
QLabel#KvValMono { font-size: 12px; color: #0F172A; font-family: "Consolas"; font-weight: 600; }
QLabel#KvErr  { font-size: 12px; color: #EF4444; }

/* Badges */
QLabel#BadgeDefault {
    background: #F4F5F7; color: #475569; border: 1px solid #E4E7EC;
    border-radius: 11px; font-size: 11px; padding: 2px 8px;
}
QLabel#BadgeSuccess {
    background: #ECFDF5; color: #047857; border: 1px solid #BBF7D0;
    border-radius: 11px; font-size: 11px; padding: 2px 8px;
}
QLabel#BadgeWarn {
    background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A;
    border-radius: 11px; font-size: 11px; padding: 2px 8px;
}
QLabel#BadgeError {
    background: #FEF2F2; color: #BE123C; border: 1px solid #FECDD3;
    border-radius: 11px; font-size: 11px; padding: 2px 8px;
}

/* Price section */
QFrame#PriceSection { background: #FFFFFF; }
QLabel#PriceTitle { font-size: 11px; color: #94A3B8; }
QLabel#PriceBestBadge {
    font-size: 11px; font-weight: 600; color: #047857;
    background: #ECFDF5; border: 1px solid #BBF7D0;
    border-radius: 999px; padding: 1px 6px;
}
QLabel#PriceHdr {
    color: #94A3B8; font-size: 10px; font-weight: 600;
    font-family: "Consolas"; letter-spacing: 0.04em;
}
QLabel#PriceQty { color: #475569; font-size: 12px; font-family: "Consolas"; }
QLabel#PriceCell { color: #0F172A; font-size: 12px; font-family: "Consolas"; }
QLabel#PriceBestQty { color: #047857; font-size: 12px; font-family: "Consolas"; font-weight: 600; }
QLabel#PriceBestCell { color: #047857; font-size: 12px; font-family: "Consolas"; font-weight: 600; }
QLabel#PriceSavings { font-size: 10px; color: #047857; }
QLabel#PriceSavingsDash { font-size: 10px; color: #94A3B8; }
QFrame#PriceRowDiv { background: #EDF0F3; }

/* Card footer */
QFrame#CardFooter {
    background: #FCFCFD; border-top: 1px solid #EDF0F3;
    border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;
}
QPushButton#FooterPrimary {
    color: #FFFFFF; border: 1px solid #2952D6; background: #3B68F1;
    font-size: 12px; font-weight: 700;
    border-radius: 6px; padding: 4px 10px; height: 28px;
}
QPushButton#FooterPrimary:hover { background: #2952D6; }
QPushButton#FooterLink {
    color: #2952D6; border: 0; background: transparent;
    font-size: 12px; font-weight: 500;
    border-radius: 6px; padding: 4px 8px; height: 28px;
}
QPushButton#FooterLink:hover { background: #EEF4FF; }
QPushButton#FooterLinkMuted {
    color: #475569; border: 0; background: transparent;
    font-size: 12px; font-weight: 500;
    border-radius: 6px; padding: 4px 8px; height: 28px;
}
QPushButton#FooterLinkMuted:hover { background: #F4F5F7; }
QPushButton#CandidateBtn {
    text-align: left; color: #1E3FAF; background: #EEF4FF;
    border: 1px solid #D5E0FF; border-radius: 7px;
    font-size: 12px; padding: 4px 8px; height: 30px;
}
QPushButton#CandidateBtn:hover { background: #DDE8FF; border-color: #B8CCFF; }
QLabel#FooterSep { background: #EDF0F3; }
QLabel#FooterTime { font-size: 11px; color: #94A3B8; }

/* Empty panel */
QFrame#EmptyPanel {
    background: #FFFFFF; border: 1px dashed #E4E7EC;
    border-radius: 12px;
}

/* Text result */
QTextEdit#TextResult {
    background: #0F172A; color: #E2E8F0; border: 0;
    border-radius: 12px; font-family: "Consolas";
    font-size: 12px; padding: 12px;
}
QTextEdit#ChatTranscript {
    background: #FFFFFF; color: #0F172A; border: 0;
    border-top: 1px solid #EDF0F3;
    font-size: 13px; padding: 16px;
}
QFrame#ChatSidebar {
    background: #F8F9FB;
    border-right: 1px solid #E4E7EC;
}
QFrame#ChatMain { background: #FFFFFF; }
QLabel#ChatSidebarTitle {
    font-size: 15px;
    font-weight: 800;
    color: #0F172A;
}
QLabel#ChatSidebarSub {
    font-size: 11px;
    color: #94A3B8;
    margin-bottom: 8px;
}
QLabel#ChatSidebarSection {
    font-size: 10px;
    font-weight: 800;
    color: #94A3B8;
    margin-top: 8px;
}
QPushButton#ChatRoomBtn, QPushButton#ChatRoomBtnActive {
    border: 0;
    border-radius: 7px;
    height: 30px;
    padding: 0 9px;
    text-align: left;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#ChatRoomBtn {
    background: transparent;
    color: #475569;
}
QPushButton#ChatRoomBtn:hover { background: #EEF0F3; }
QPushButton#ChatRoomBtnActive {
    background: #EEF4FF;
    color: #1E3FAF;
}
QLabel#ChatMemberItem, QPushButton#ChatMemberItem {
    color: #475569;
    font-size: 12px;
    padding: 3px 4px;
}
QPushButton#ChatMemberItem {
    border: 0;
    border-radius: 7px;
    background: transparent;
    text-align: left;
}
QPushButton#ChatMemberItem:hover { background: #EEF0F3; }
QLabel#ChatHint {
    color: #94A3B8;
    font-size: 10px;
}
QTextEdit#ChatMessageInput {
    background: #FFFFFF; color: #0F172A; border: 1px solid #D0D5DD;
    border-radius: 8px; font-size: 13px; padding: 8px 10px;
}
QTextEdit#ChatMessageInput:focus { border: 1px solid #3B68F1; }
QFrame#ChatHeader {
    background: #FFFFFF;
    border-bottom: 1px solid #E4E7EC;
}
QLabel#ChatChannelAvatar {
    background: #0F172A;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 18px;
    font-weight: 800;
}
QLabel#ChatTitle {
    font-size: 15px;
    font-weight: 800;
    color: #0F172A;
}
QLabel#ChatSubtitle {
    font-size: 12px;
    color: #64748B;
}
QFrame#ChatControls {
    background: #F8F9FB;
    border-bottom: 1px solid #E4E7EC;
}
QFrame#ChatControls QLineEdit {
    background: #FFFFFF;
    border: 1px solid #D0D5DD;
    border-radius: 7px;
    padding: 5px 8px;
    height: 28px;
}
QFrame#ChatControls QLineEdit:focus { border-color: #3B68F1; }
QFrame#ChatActionBar {
    background: #FFFFFF;
    border-bottom: 1px solid #EDF0F3;
}
QPushButton#ChatAction {
    background: #FFFFFF;
    border: 1px solid #D0D5DD;
    border-radius: 7px;
    color: #475569;
    font-size: 12px;
    font-weight: 700;
    height: 30px;
    padding: 0 12px;
}
QPushButton#ChatAction:hover {
    background: #F4F5F7;
    border-color: #B8BFC8;
}
QFrame#ChatComposer {
    background: #F8F9FB;
    border-top: 1px solid #E4E7EC;
}
QFrame#ChatComposer QPushButton#Primary {
    height: 34px;
    padding: 0 16px;
    border-radius: 8px;
    font-weight: 800;
}

/* Status bar */
QFrame#Statusbar {
    background: #FAFBFC; border-top: 1px solid #E4E7EC;
}
QLabel#SbItem { font-size: 11px; color: #94A3B8; }
QLabel#SbOk   { font-size: 11px; color: #047857; }

/* Scroll area */
QScrollArea { border: 0; background: #FFFFFF; }
QScrollArea > QWidget > QWidget { background: #FFFFFF; }
QScrollBar:vertical {
    width: 10px; background: transparent; border: 0; margin: 0;
}
QScrollBar::handle:vertical {
    background: #D6DAE0; border-radius: 5px;
    min-height: 20px; margin: 2px;
}
QScrollBar::handle:vertical:hover { background: #B8BFC8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
