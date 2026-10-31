# Superinvestors × initiés

**Univers :** les valeurs du S&P 500 de la grille Dataroma (« Last qtr buys » par défaut) détenues par au moins 1 superinvestor (réglable).

Deux analyses **séparées** sont menées :

| | Source | Règle de sélection |
|---|---|---|
| **A. Dataroma** | tableau « Total insider Buys/Sells last 6 months » de chaque fiche | solde $ > 0 (méthode du fichier initial) |
| **B. OpenInsider** | transactions des N derniers jours, **levées d'options toujours exclues**, sur **tout le S&P 500** par défaut (500 valeurs, environ 5 s) ou sur les seules valeurs suivies par les superinvestors | au choix : acheteurs distincts > vendeurs (défaut), nb achats > nb ventes, ou solde $ > 0 |

Le **tableau final** reprend les colonnes du tableau initial Dataroma, ajoute les indicateurs OpenInsider et une colonne **« Retenue par »** : Dataroma, OpenInsider ou les deux. Une valeur est retenue dès qu'**une** des deux analyses la sélectionne. On n'exige pas les deux à la fois.

## Indicateurs OpenInsider

- **Initiés OpenInsider** : résumé avec pastilles. Exemple : `🟢🟢 achats groupés (2 en 30 j), dont CEO +15.3 M$ · ventes 2.0 M$`.
  - 🟢🟢 achats groupés et plus d'acheteurs que de vendeurs
  - 🟢 plus d'acheteurs que de vendeurs
  - 🟠 autant ou plus de vendeurs
  - ⚪ aucune transaction
- **Acheteurs / vendeurs distincts** : nombre d'initiés différents, plus fiable que le montant.
- **Achat groupé** : nombre maximal d'acheteurs différents sur 30 jours (signal fort à partir de 2).
- **Max ΔOwn** : plus forte hausse de participation d'un acheteur (100 = nouvelle position). Le filtre « ΔOwn minimum » permet d'exiger, par exemple, une hausse d'au moins 50 %.
- **Cas atypique** : actionnaire à plus de 10 % (ex. Berkshire Hathaway chez LEN), entité (fonds, holding, trust) ou transaction d'au moins 50 M$.
- **Option « Exclure les actionnaires >10 % »** : ne garde que les dirigeants et administrateurs.
- **Montant minimum par achat** (défaut **50 000 $** ; l'achat médian d'un initié du S&P 500 est d'environ 90 000 $) : les achats plus petits sont ignorés (achats automatiques, sommes symboliques). **Les ventes sont toutes comptées**, sinon une valeur pourrait passer « acheteurs > vendeurs » simplement parce que ses petites ventes auraient disparu. 500 000 $ correspond à un réglage « forte conviction », mais il peut faire disparaître des achats groupés d'administrateurs.

Les filtres (critère, montant minimum par achat, actionnaires >10 %, ΔOwn, achats groupés) s'appliquent **instantanément**, sans nouveau téléchargement. Seuls la page Dataroma, le nombre de superinvestors, les valeurs analysées et la période demandent de relancer l'analyse.

## Sentiment des initiés

En haut de l'interface, un encadré donne le sentiment des initiés de l'univers analysé sur la période choisie, comparé au choix :

- à la **même période l'an dernier** (défaut) : même saison, même calendrier de publication des résultats ;
- à la **période précédente** : par exemple août–octobre contre mai–juillet, pour suivre la tendance récente.

Indicateurs :

- ratio acheteurs distincts / vendeurs distincts ;
- ratio nombre d'achats / nombre de ventes ;
- ratio montants achats / ventes ;
- nombre de valeurs où les acheteurs sont plus nombreux que les vendeurs.

On compare à la même saison parce que les initiés ne peuvent pas négocier pendant les semaines qui précèdent la publication des résultats. Le niveau d'activité dépend donc beaucoup du calendrier. Les ventes dépassent toujours largement les achats dans les grandes capitalisations : c'est la **variation** du ratio qui renseigne, pas son niveau. Les mêmes filtres (montant minimum par achat, actionnaires >10 %) s'appliquent aux deux périodes. La comparaison ajoute environ 5 secondes. En ligne de commande : `--comparer an`, `--comparer precedente` ou `--comparer aucune`. Le détail figure dans l'onglet « Sentiment » de l'export Excel.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Interface web

```bash
streamlit run app.py
```

L'interface a cinq onglets :

- **Tableau final** : les valeurs retenues par au moins une des deux analyses.
- **A. Dataroma** : la sélection de l'analyse Dataroma seule.
- **B. OpenInsider** : la sélection de l'analyse OpenInsider seule.
- **Transactions** : le détail ligne par ligne des transactions OpenInsider.
- **Diagnostic** : le journal de chaque requête OpenInsider (adresse, code HTTP, nombre de lignes). Si OpenInsider ne renvoie rien, un avertissement s'affiche et ce journal permet de comprendre pourquoi.

Exports : page HTML triable, Excel (Sélection, Toutes les valeurs, Transactions) et CSV.

Avec « Tout le S&P 500 », les valeurs sans superinvestor ont leurs colonnes « DR » vides : leur fiche Dataroma n'est pas lue par défaut. Le bouton « Lire leur fiche Dataroma » au-dessus du tableau final la lit seulement pour les valeurs affichées. Ces données sont présentées pour information ; elles ne font pas entrer la valeur dans la sélection Dataroma, qui reste limitée à l'univers superinvestors.

Durée : environ 1 min 30 avec l'analyse Dataroma (une requête par fiche), environ 5 secondes sans elle. Pour la désactiver, décochez « Lire le résumé initiés de chaque fiche ».

## Ligne de commande

```bash
python analyse.py                                  # A + B, ≥ 1 superinvestor, critère acheteurs > vendeurs
python analyse.py --critere usd --sans-10pct       # solde $ > 0, sans actionnaires >10 %
python analyse.py --delta-min 50 --groupes         # ΔOwn ≥ 50 % et achats groupés
python analyse.py --sans-dataroma                  # OpenInsider seul, ≈ 5 s
python analyse.py --montant-min 500000             # forte conviction (défaut : 50 000 $)
python analyse.py --univers-si                     # OpenInsider limité aux valeurs des superinvestors
```

Le script produit `selection_inities.xlsx` et `selection_inities.html`.

## Fichiers

| Fichier | Rôle |
|---|---|
| `app.py` | interface Streamlit |
| `analyse.py` | univers, analyses A et B, tableau final, exports, ligne de commande |
| `dataroma_scraper.py` | lecture des pages Dataroma (fichier initial, inchangé) |
| `openinsider.py` | lecture des pages OpenInsider et calcul des indicateurs |
| `exports.py` | export Excel et page HTML |

## Remarques

- Pour OpenInsider, la période se base sur la date de déclaration à la SEC.
- Les données Dataroma couvrent 6 mois et ne permettent pas d'exclure les levées d'options.
- Respectez les conditions d'utilisation des deux sites.
- Ces données sont fournies à titre d'information et ne constituent pas un conseil en investissement.
