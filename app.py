"""
Interface Streamlit : streamlit run app.py
"""
from datetime import date

import pandas as pd
import streamlit as st

import analyse as an
import openinsider as oi
from dataroma_scraper import GRIDS

st.set_page_config(page_title="Superinvestors × initiés", page_icon="📈", layout="wide")
st.title("Superinvestors × initiés")
st.caption("Univers : valeurs du S&P 500 suivies par les superinvestors (dataroma.com), "
           "ou tout le S&P 500 pour OpenInsider. "
           "Deux analyses séparées : résumé initiés 6 mois de Dataroma, et transactions "
           "OpenInsider (levées d'options exclues).")

with st.sidebar:
    st.header("Univers")
    grid = st.selectbox("Page Dataroma", list(GRIDS), format_func=lambda k: GRIDS[k])
    min_si = st.number_input("Nb minimum de superinvestors", 1, 50, 1)
    st.header("A. Dataroma")
    with_dr = st.checkbox("Lire le résumé initiés de chaque fiche (≈ 1 min 30)", value=True,
                          help="Porte uniquement sur les valeurs suivies par les superinvestors.")
    st.header("B. OpenInsider")
    scope = st.radio("Valeurs analysées", ["si", "sp500"], index=1,
                     format_func=lambda k: {"si": "Suivies par les superinvestors",
                                            "sp500": "Tout le S&P 500 (500 valeurs, ≈ 5 s)"}[k])
    days = st.select_slider("Période (jours de déclaration)", [30, 60, 90, 120, 180], 90)
    compare = st.radio("Sentiment comparé à (≈ +5 s)", list(an.COMPARE),
                       format_func=lambda k: an.COMPARE[k],
                       help="L'an dernier : même saison, même calendrier de résultats. "
                            "Période précédente : ex. août–octobre contre mai–juillet, "
                            "pour voir la tendance récente.")
    go = st.button("Lancer l'analyse", type="primary", width="stretch")
    st.subheader("Filtres (instantanés)")
    criterion = st.radio("Critère", list(oi.CRITERIA), format_func=lambda k: oi.CRITERIA[k])
    min_value = st.select_slider(
        "Montant minimum par achat ($)",
        [0, 25_000, 50_000, 90_000, 100_000, 250_000, 500_000, 1_000_000], an.DEFAULT_MIN_BUY,
        format_func=lambda v: "aucun" if v == 0 else f"{v:,.0f} $".replace(",", " "),
        help="Ignore les achats plus petits (achats automatiques, montants symboliques). "
             "Les ventes sont toutes comptées. 50 000 $ par défaut ; 90 000 $ ≈ achat médian ; "
             "500 000 $ = forte conviction (mais peut casser les achats groupés).")
    excl10 = st.checkbox("Exclure les actionnaires >10 %", value=False,
                         help="Ex. Berkshire Hathaway, déclaré initié chez Lennar.")
    min_delta = st.slider("ΔOwn minimum d'un acheteur (%)", 0, 100, 0, 5,
                          help="50 % = un dirigeant a augmenté sa position de moitié.")
    cluster_only = st.checkbox("Seulement les achats groupés (≥ 2 acheteurs en 30 j)")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load(grid, min_si, with_dr, scope, days, compare):
    bar = st.progress(0.0, text="Grille Dataroma…")
    base = an.sp500(grid)
    uni = an.universe(grid, min_si, base)
    oi_uni = base if scope == "sp500" else uni
    dr_df = None
    if with_dr:
        dr_df = an.run_dataroma(uni, progress=lambda i, n, t: bar.progress(
            i / n * 0.9, text=f"Dataroma {i}/{n} – {t}"))
    raw_tx, log = an.fetch_openinsider(oi_uni, days, progress=lambda i, n, t: bar.progress(
        0.9 + i / n * 0.05, text=f"OpenInsider {i}/{n}"))
    prev_tx = None
    if compare != "aucune":
        prev_tx, log_prev = an.fetch_openinsider(
            oi_uni, days, years_back=int(compare == "an"),
            periods_back=int(compare == "precedente"), progress=lambda i, n, t: bar.progress(
                0.95 + i / n * 0.05, text=f"OpenInsider comparaison {i}/{n}"))
        log = log + [dict(e, periode=an.COMPARE[compare]) for e in log_prev]
    bar.empty()
    return uni, oi_uni, dr_df, raw_tx, log, prev_tx


if go:
    try:
        st.session_state["data"] = load(grid, int(min_si), with_dr, scope, int(days), compare)
        st.session_state["cmp"] = compare
        st.session_state.pop("dr_extra", None)
        st.session_state["p"] = (grid, int(min_si), with_dr, int(days), scope)
    except Exception as e:  # noqa: BLE001
        st.error(f"Erreur : {e}")

if "data" not in st.session_state:
    st.info("Réglez les paramètres puis cliquez sur **Lancer l'analyse**.")
    st.stop()

uni, oi_uni, dr_df, raw_tx, log, prev_raw = st.session_state["data"]
g, m, wdr, d, sc = st.session_state["p"]
tx = an.filter_tx(raw_tx, excl10, min_value)
oi_df = oi.summarize(tx, oi_uni["ticker"].tolist())
extra = st.session_state.get("dr_extra")
dr_all = dr_df if extra is None or dr_df is None else pd.concat([dr_df, extra], ignore_index=True)
final = an.combine(oi_uni, dr_all, oi_df, criterion, min_delta, cluster_only,
                   dr_universe=set(uni["ticker"]))
prev_tx = an.filter_tx(prev_raw, excl10, min_value) if prev_raw is not None else None
s_now = oi.sentiment(tx)
s_prev = oi.sentiment(prev_tx) if prev_tx is not None else None
cmp_mode = st.session_state.get("cmp", "an")
sent = an.sentiment_table(s_now, s_prev, d, cmp_mode)
p_prev = an.compare_range(d, cmp_mode)
sel = final[final["selected_by"] != ""]

if raw_tx.empty:
    st.warning("OpenInsider n'a renvoyé aucune transaction : voir l'onglet **Diagnostic**. "
               "Ouvrez le premier lien du journal dans votre navigateur pour vérifier.")

c = st.columns(5)
c[0].metric("Univers OpenInsider" if sc == "sp500" else "Univers", len(oi_uni))
c[1].metric("Retenues Dataroma", int(final["dr_ok"].sum()))
c[2].metric("Retenues OpenInsider", int(final["oi_ok"].sum()))
c[3].metric("Les deux", int((final["dr_ok"] & final["oi_ok"]).sum()))
c[4].metric("Achats groupés", int((final["cluster"] >= 2).sum()))

money = {an.LABELS[k]: st.column_config.NumberColumn(format="$%d")
         for k in ("ins_buy_usd", "ins_sell_usd", "dr_balance_usd",
                   "buy_usd", "sell_usd", "balance_usd")}
cfg = money | {
    an.LABELS["url"]: st.column_config.LinkColumn(display_text="fiche"),
    an.LABELS["oi_url"]: st.column_config.LinkColumn(display_text="fiche"),
    an.LABELS["oi_signal"]: st.column_config.TextColumn(width="large"),
    an.LABELS["max_delta_own"]: st.column_config.NumberColumn(format="%.0f %%"),
}

with st.container(border=True):
    st.markdown(f"**Sentiment des initiés** · {'tout le S&P 500' if sc == 'sp500' else 'univers superinvestors'}"
                f" · {d} derniers jours" + (f" · comparé au {p_prev[0]:%d/%m/%Y} → {p_prev[1]:%d/%m/%Y}"
                   f" ({an.COMPARE[cmp_mode].lower()})" if s_prev and p_prev else ""))

    def _metric(col, label, key, fmt="{:.3f}"):
        a = s_now.get(key)
        b = s_prev.get(key) if s_prev else None
        delta = (f"{(a / b - 1):+.0%} {an.COMPARE_SHORT.get(cmp_mode, '')}"
                 if a is not None and b else None)
        col.metric(label, "–" if a is None else fmt.format(a), delta,
                   help=None if b is None else f"Période de comparaison : {fmt.format(b)}")

    k = st.columns(4)
    _metric(k[0], "Acheteurs / vendeurs", "ratio_ins")
    _metric(k[1], "Nb achats / nb ventes", "ratio_tx")
    _metric(k[2], "Montants achats / ventes", "ratio_usd")
    _metric(k[3], "Valeurs acheteurs > vendeurs", "valeurs_pos", "{:.0f}")
    st.caption("L'an dernier : compare à la même saison (même calendrier de résultats). "
               "Période précédente : montre la tendance récente, mais les deux périodes "
               "ne contiennent pas forcément le même nombre de jours de négociation autorisée. "
               "Les ventes dépassent toujours largement les achats dans les grandes capitalisations : "
               "c'est l'évolution qui compte, pas le niveau.")
    with st.expander("Détail"):
        st.dataframe(sent, hide_index=True, width="stretch", column_config={
            "Variation": st.column_config.NumberColumn(format="percent")})

VIEWS = {
    "union": ("Au moins une source", final["dr_ok"] | final["oi_ok"]),
    "both": ("Les deux sources", final["dr_ok"] & final["oi_ok"]),
    "oi": ("OpenInsider", final["oi_ok"]),
    "dr": ("Dataroma", final["dr_ok"]),
}
which = st.segmented_control(
    "Afficher", list(VIEWS), default="union",
    format_func=lambda k: f"{VIEWS[k][0]} ({int(VIEWS[k][1].sum())})",
    help="Au moins une source = retenue par Dataroma OU par OpenInsider. "
         "Les deux sources = retenue par Dataroma ET par OpenInsider.")
view = final[VIEWS[which or "union"][1]]
pick = st.multiselect("Secteur", sorted(final["sector"].dropna().unique()))
if pick:
    view = view[view["sector"].isin(pick)]

t1, t2, t3, t4, t5 = st.tabs(["Tableau final", "A. Dataroma", "B. OpenInsider",
                              "Transactions", "Diagnostic"])
with t1:
    if dr_df is not None and "ins_buy_n" in view:
        missing = view.loc[view["ins_buy_n"].isna() & ~view["ticker"].isin(uni["ticker"]), "ticker"]
        if len(missing):
            c1, c2 = st.columns([3, 1])
            c1.caption(f"Colonnes « DR » vides pour {len(missing)} valeur(s) hors univers "
                       "superinvestors : leur fiche Dataroma n'est pas lue par défaut.")
            if c2.button(f"Lire leur fiche Dataroma (≈ {max(1, round(len(missing) * 0.7))} s)"):
                with st.spinner("Lecture des fiches Dataroma…"):
                    new = an.run_dataroma(pd.DataFrame({"ticker": missing.tolist()}))
                st.session_state["dr_extra"] = new if extra is None else pd.concat(
                    [extra, new], ignore_index=True)
                st.rerun()
    st.dataframe(an.display(view), width="stretch", hide_index=True, column_config=cfg)
    st.caption("**Qui achète ?** « Superinvestors » = fonds (déclarations trimestrielles 13F). "
               "« Initiés » = dirigeants et administrateurs de la société (formulaires 4), "
               "vus par Dataroma sur 6 mois et par OpenInsider sur la période choisie. "
               "Le choix « Afficher » filtre les lignes, il ne change pas le sens des colonnes.")
    st.caption("🟢🟢 achats groupés et plus d'acheteurs que de vendeurs · 🟢 plus d'acheteurs "
               "· 🟠 autant ou plus de vendeurs · ⚪ aucune transaction. "
               "Cas atypique : actionnaire >10 %, entité (fonds, holding) ou montant ≥ 50 M$.")
with t2:
    if dr_df is None:
        st.info("Analyse Dataroma désactivée dans la barre latérale.")
    else:
        cols = ["ticker", "name", "sector", "si_count", "ins_buy_n", "ins_buy_usd",
                "ins_sell_n", "ins_sell_usd", "dr_balance_usd", "url"]
        st.dataframe(an.display(final[final["dr_ok"]][cols]), width="stretch",
                     hide_index=True, column_config=cfg)
with t3:
    cols = ["ticker", "name", "si_count", "oi_signal", "buyers", "sellers", "buy_tx", "sell_tx",
            "buy_usd", "sell_usd", "balance_usd", "max_delta_own", "cluster", "atypical",
            "buyer_names", "oi_url"]
    st.dataframe(an.display(final[final["oi_ok"]][cols]), width="stretch",
                 hide_index=True, column_config=cfg)
with t4:
    tk = st.selectbox("Valeur", ["(toutes)"] + (sorted(tx["ticker"].unique()) if not tx.empty else []))
    st.dataframe(an.display_tx(tx if tk == "(toutes)" else tx[tx["ticker"] == tk]),
                 width="stretch", hide_index=True)
with t5:
    st.write(f"{len(raw_tx)} transactions OpenInsider lues, {len(tx)} après filtres.")
    st.dataframe(pd.DataFrame(log), width="stretch", hide_index=True)

note = an.make_note(g, m, d, criterion, excl10, wdr, sc, min_value)
stamp = f"{date.today():%Y%m%d}"
b = st.columns(3)
b[0].download_button("⬇️ Page HTML", an.export_html(view, "Superinvestors × initiés", note)
                     .encode("utf-8"), f"selection_{stamp}.html", "text/html", width="stretch")
b[1].download_button("⬇️ Excel (3 onglets)", an.export_excel(final, tx, note, sent),
                     f"selection_{stamp}.xlsx",
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     width="stretch")
b[2].download_button("⬇️ CSV", an.display(view).to_csv(index=False).encode("utf-8-sig"),
                     f"selection_{stamp}.csv", "text/csv", width="stretch")
st.caption(note + " Informations à titre indicatif, pas un conseil en investissement.")
