using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // La fiche de la province gardée sur la carte. Elle dit d'abord le pays du lieu cliqué (`/terres`), puis ce lieu, sa
    // province et son seigneur, la date, et chaque lieu de la province (`/lieu`). Chaque nombre d'habitants dit ce qu'il compte :
    // le pays, le lieu ou la province. Le titre du panneau porte le nom de la province. Rien n'est additionné ici.
    public sealed class DossierTerritoire : MonoBehaviour
    {
        Text texte, titre;
        Func<CelluleDeCarte> selection;
        Func<long> rang;
        Func<TerresDeLaCarte> terres;
        LectureDossier lecture;
        ScrollRect defilement;
        long? cellule; long? rangLu;
        double prochaineLecture;
        public DocumentDuMonde Document => lecture?.Document;
        // `rang` : celui du lieu cliqué dans la terre (0, le bourg, s'il manque) ; `terres` : les terres de `/terres`, nulles tant qu'elles ne sont pas lues ;
        // `titre` : le texte du titre du panneau, qui prend le nom de la province.
        public void Initialiser(Text contenu, int port, Func<CelluleDeCarte> selection, Func<long> rang = null, Func<TerresDeLaCarte> terres = null, Text titre = null)
        {
            texte = contenu; this.selection = selection; this.rang = rang; this.terres = terres; this.titre = titre; lecture = LectureDossier.Locale(port);
            var ancien = texte.rectTransform;
            var cadre = new GameObject("Lecture du territoire", typeof(RectTransform), typeof(Image), typeof(RectMask2D), typeof(ScrollRect)).GetComponent<RectTransform>();
            cadre.SetParent(ancien.parent, false);
            cadre.anchorMin = ancien.anchorMin; cadre.anchorMax = ancien.anchorMax; cadre.pivot = ancien.pivot;
            cadre.anchoredPosition = ancien.anchoredPosition; cadre.sizeDelta = ancien.sizeDelta;
            cadre.GetComponent<Image>().color = Color.clear;
            ancien.SetParent(cadre, false);
            ancien.anchorMin = new Vector2(0, 1); ancien.anchorMax = Vector2.one; ancien.pivot = new Vector2(0, 1);
            ancien.anchoredPosition = Vector2.zero; ancien.sizeDelta = new Vector2(0, cadre.sizeDelta.y);
            defilement = cadre.GetComponent<ScrollRect>();
            defilement.viewport = cadre; defilement.content = ancien;
            defilement.horizontal = false; defilement.inertia = false; defilement.scrollSensitivity = 24;
            defilement.movementType = ScrollRect.MovementType.Clamped;
            texte.supportRichText = false;
        }
        void OnDestroy() => lecture?.Vider();
        void LateUpdate() => Pas(Time.realtimeSinceStartupAsDouble);
        // Relit `/lieu` de la terre gardée (à son changement, puis toutes les deux secondes) et récrit la fiche et le titre ; rien sans terre gardée.
        public void Pas(double maintenant)
        {
            var choisie = selection?.Invoke();
            if (choisie == null || lecture == null) return;
            long lieu = rang?.Invoke() ?? 0;
            bool change = cellule != choisie.CellId;
            if (change || rangLu != lieu) { cellule = choisie.CellId; rangLu = lieu; defilement.verticalNormalizedPosition = 1; }
            if (change || !lecture.EnCours && maintenant >= prochaineLecture)
            {
                prochaineLecture = maintenant + 2;
                _ = lecture.Actualiser("/lieu?cell=" + choisie.CellId);
            }
            texte.text = Texte(lecture.Erreur, lecture.Document, terres?.Invoke(), choisie.CellId, lieu);
            if (titre != null) titre.text = Titre(lecture.Erreur == null ? lecture.Document : null, choisie.CellId);
            texte.rectTransform.sizeDelta = new Vector2(0, Mathf.Max(defilement.viewport.rect.height, texte.preferredHeight + 16));
        }

        public const string ATTENTE = "Lecture de la terre, de ses lieux et de ses réserves…";
        public const string PAYS_EN_LECTURE = "Pays en lecture…";
        public const string SANS_ETAT = "Terre sans État : aucun pays ne la tient, on ne la joue pas";
        public const string PROVINCE_EN_LECTURE = "Province en lecture";
        const string PAYS_SANS_NOM = "Pays sans nom";

        // Le titre du panneau : « Province de » et le nom servi de son bourg, ou l'attente tant que le dossier de cette terre n'est pas lu.
        public static string Titre(DocumentDuMonde document, long cellule)
        {
            if (document == null) return PROVINCE_EN_LECTURE;
            try { return "Province " + De(Nom(EnTete(document, cellule, 0).lieux.First(l => DocumentDuMonde.Entier(l, "rang") == 0))); }
            catch (ArgumentException) { return PROVINCE_EN_LECTURE; }
        }

        // La fiche entière : les lignes du pays, puis celles du dossier, ou son attente, ou la cause d'une lecture manquée.
        // Une raison qui montre la cellule ou un nombre nu se tait devant le joueur.
        public static string Texte(string erreur, DocumentDuMonde document, TerresDeLaCarte terres, long cellule, long rang)
        {
            if (erreur != null || document == null) return string.Join("\n", LignesDuPays(terres, cellule, rang).Concat(LignesDuLieu(erreur, document, cellule, rang)));
            try { return Decrire(document, terres, cellule, rang); }
            catch (ArgumentException e) { return string.Join("\n", LignesDuPays(terres, cellule, rang)) + "\nDossier incomplet : " + TexteDuMonde.Absence(e.Message, cellule.ToString(CultureInfo.InvariantCulture)); }
        }

        // Les lignes du pays du lieu, d'après `/terres` : son nom, son suzerain (ou, sans suzerain, l'ensemble qu'il porte) et ses habitants servis.
        // Une terre sans pays le dit, et dit qu'on ne la joue pas ; avant la lecture des terres, l'attente.
        public static List<string> LignesDuPays(TerresDeLaCarte terres, long cellule, long rang)
        {
            if (terres == null) return new List<string> { PAYS_EN_LECTURE };
            string pays = terres.PaysDuLieu(cellule, rang);
            if (pays == null) return new List<string> { SANS_ETAT };
            string nom = terres.NomDuPays(pays) ?? PAYS_SANS_NOM;
            var lignes = new List<string> { nom };
            string suzerain = terres.SuzerainDe(pays), ensemble = terres.EnsembleDe(pays);
            if (suzerain != null) lignes.Add("Suzerain : " + (terres.NomDuPays(suzerain) ?? PAYS_SANS_NOM));
            else if (ensemble != null) lignes.Add("Ensemble : " + ensemble);
            lignes.Add(nom + " : " + (terres.HabitantsDu(pays) is long n ? Habitants(n) : "habitants non servis"));
            return lignes;
        }

        // Les lignes du lieu, d'après `/lieu` : le lieu et ses habitants, sa province et les siens, puis le seigneur du lieu ; ou l'attente, ou la cause.
        public static List<string> LignesDuLieu(string erreur, DocumentDuMonde document, long cellule, long rang)
        {
            string id = cellule.ToString(CultureInfo.InvariantCulture);
            try { return erreur != null ? new List<string> { "Lecture indisponible : " + TexteDuMonde.Absence(erreur, id) } : document == null ? new List<string> { ATTENTE } : EnTete(document, cellule, rang).lignes; }
            catch (ArgumentException e) { return new List<string> { "Dossier incomplet : " + TexteDuMonde.Absence(e.Message, id) }; }
        }

        static string Nombre(double n) => n.ToString("0.##", CultureInfo.GetCultureInfo("fr-FR"));
        static string Habitants(long n) => TexteDuMonde.Nombre(n) + (n > 1 ? " habitants" : " habitant");
        static string Personnes(long n, string fait) => TexteDuMonde.Nombre(n) + (n > 1 ? " personnes " + fait + "s" : " personne " + fait);

        // Les trois lignes du lieu de ce rang et les lieux servis, dans l'ordre servi ; refuse une terre différente, des lieux absents ou répétés, un bourg ou un lieu manquant.
        static (List<string> lignes, List<Dictionary<string, object>> lieux) EnTete(DocumentDuMonde document, long cellule, long rang)
        {
            var racine = document.Champs;
            if (DocumentDuMonde.Entier(racine, "cell_id") != cellule) throw new ArgumentException("Territoire différent de la sélection");
            var lieux = DocumentDuMonde.Tableau(racine, "lieux").Select(l => l as Dictionary<string, object> ?? throw new ArgumentException("Lieu illisible")).ToList();
            if (lieux.Count == 0) throw new ArgumentException("Aucun lieu transmis");
            var rangs = new HashSet<long>();
            foreach (var l in lieux) if (!rangs.Add(DocumentDuMonde.Entier(l, "rang"))) throw new ArgumentException("Rang de lieu répété");
            var bourg = lieux.FirstOrDefault(l => DocumentDuMonde.Entier(l, "rang") == 0) ?? throw new ArgumentException("Bourg absent de la terre");
            var lieu = lieux.FirstOrDefault(l => DocumentDuMonde.Entier(l, "rang") == rang) ?? throw new ArgumentException("Lieu absent de la terre");
            var lignes = new List<string>
            {
                Nom(lieu) + " : " + Habitants(DocumentDuMonde.Entier(lieu, "population")) + " dans ce lieu",
                "Province " + De(Nom(bourg)) + " : " + Habitants(DocumentDuMonde.Entier(racine, "population")),
                Seigneur(racine, lieu),
            };
            return (lignes, lieux);
        }

        // « de » devant un nom, élidé devant une voyelle (« d'Avignon », « d'Évreux ») ; un nom qui porte déjà sa particule
        // (« de Basse Haie », « d'Armagnac ») la garde seule.
        public static string De(string nom)
        {
            if (nom.StartsWith("de ", StringComparison.Ordinal) || nom.StartsWith("d'", StringComparison.Ordinal) || nom.StartsWith("d’", StringComparison.Ordinal)) return nom;
            return nom.Length > 0 && "aeiouyàâäéèêëîïôöûùüÿœ".IndexOf(char.ToLowerInvariant(nom[0])) >= 0 ? "d'" + nom : "de " + nom;
        }

        static string Nom(Dictionary<string, object> lieu) => DocumentDuMonde.Valeur(lieu, "nom") as string ?? "Nom du lieu non transmis";

        // La fiche lue : les lignes du pays et du lieu de ce rang, la date, puis chaque lieu par son nom, avec son pays quand ce n'est pas celui du bourg.
        public static string Decrire(DocumentDuMonde document, TerresDeLaCarte terres, long cellule, long rang)
        {
            var (lignes, lieux) = EnTete(document, cellule, rang);
            if (document.Annee == null) throw new ArgumentException("Date non transmise");
            var racine = document.Champs;
            var texte = new StringBuilder(string.Join("\n", LignesDuPays(terres, cellule, rang).Concat(lignes))).Append('\n').Append(TexteDuMonde.Date(new DateDuMonde(document.Annee.Value, document.JourDeLAnnee.Value))).Append('\n');
            string paysDuBourg = terres?.PaysDuLieu(cellule, 0);
            foreach (var lieu in lieux)
            {
                long r = DocumentDuMonde.Entier(lieu, "rang");
                string pays = terres?.PaysDuLieu(cellule, r);
                texte.Append("\n").Append(Nom(lieu));
                if (terres != null && pays != paysDuBourg) texte.Append(" · ").Append(pays == null ? "sans pays" : terres.NomDuPays(pays) ?? PAYS_SANS_NOM);
                texte.Append('\n');
                texte.Append(Habitants(DocumentDuMonde.Entier(lieu, "population"))).Append(" dans ce lieu · ");
                texte.Append(Nombre(DocumentDuMonde.Nombre(lieu, "surface_km2"))).Append(" km²\n");
                texte.Append(Seigneur(racine, lieu)).Append('\n');
                var stocks = DocumentDuMonde.Objet(lieu, "stocks");
                if (stocks.Count == 0) texte.Append("Réserves : panier vide\n");
                foreach (var cle in stocks.Keys.OrderBy(c => c))
                    texte.Append(cle).Append(" : ").Append(TexteDuMonde.Masse(DocumentDuMonde.Nombre(stocks, cle))).Append('\n');
                var flux = DocumentDuMonde.Valeur(lieu, "flux_30j") as Dictionary<string, object>;
                if (flux == null) texte.Append("Flux non transmis\n");
                else
                {
                    texte.Append("Sur 30 jours : ").Append(TexteDuMonde.Masse(DocumentDuMonde.Nombre(flux, "preleve_kg"))).Append(" prélevés\n");
                    texte.Append(Personnes(DocumentDuMonde.Entier(flux, "partis_personnes"), "partie")).Append(" · ")
                        .Append(Personnes(DocumentDuMonde.Entier(flux, "arrives_personnes"), "arrivée")).Append('\n');
                }
            }
            return texte.ToString();
        }

        // Le seigneur du lieu : la maison de son maître, nommée par le dossier ; « Sans seigneur » pour un lieu sans maître.
        static string Seigneur(Dictionary<string, object> racine, Dictionary<string, object> lieu)
        {
            var maitre = DocumentDuMonde.Valeur(lieu, "maitre");
            if (maitre == null) return "Sans seigneur";
            var maisons = DocumentDuMonde.Objet(DocumentDuMonde.Objet(racine, "noms"), "maisons");
            if (!(maitre is string id) || !maisons.TryGetValue(id, out var fiche)
                || !(fiche is Dictionary<string, object> maison)) return "Seigneur : nom non transmis";
            return "Seigneur : Maison " + (DocumentDuMonde.Valeur(maison, "nom") as string ?? "nom non transmis");
        }
    }
}
