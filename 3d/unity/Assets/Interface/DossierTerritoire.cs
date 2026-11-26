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
    // La fiche de la province gardée sur la carte. Elle dit d'abord le pays du lieu cliqué, sur une ligne (`/terres`), puis ce lieu, sa
    // province et son seigneur, la date, et chaque lieu de la province (`/lieu`). Chaque nombre d'habitants dit ce qu'il compte :
    // le pays, le lieu ou la province ; une province dont les lieux sont de plusieurs pays les nomme, pour que ses habitants, tous
    // pays confondus, ne contredisent pas ceux du pays. Le titre du panneau porte le nom de la province. Rien n'est additionné ici.
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
        // Une terre que le joueur ne joue pas : un pays servi sans maison (une terre sans État nommée), ou un lieu sans pays.
        public const string SANS_ETAT = "Terre sans État", ON_NE_LA_JOUE_PAS = "on ne la joue pas", AUCUN_PAYS = "aucun pays ne la tient";
        public const string PROVINCE_EN_LECTURE = "Province en lecture";
        // Le seigneur d'un lieu dont la maison est plausible : le monde le sert comme une désignation, jamais comme une maison de l'histoire.
        public const string SEIGNEUR_LOCAL = "Seigneur local, que l'histoire ne nomme pas";
        public const string SORTE_PLAUSIBLE = "plausible", SORTE_GRANDE_MAISON = "grande maison", SORTE_SEIGNEURIE = "seigneurie";
        const string PAYS_SANS_NOM = "Pays sans nom", LIEUX_SANS_MAITRE = "lieux sans maître";
        const string SEP = " · ";

        // Le titre du panneau : « Province de » et le nom servi de son bourg, ou l'attente tant que le dossier de cette terre n'est pas lu.
        public static string Titre(DocumentDuMonde document, long cellule)
        {
            if (document == null) return PROVINCE_EN_LECTURE;
            try { return "Province " + De(Nom(EnTete(document, null, cellule, 0).lieux.First(l => DocumentDuMonde.Entier(l, "rang") == 0))); }
            catch (ArgumentException) { return PROVINCE_EN_LECTURE; }
        }

        // La fiche entière : les lignes du pays, puis celles du dossier, ou son attente, ou la cause d'une lecture manquée.
        // Une raison qui montre la cellule ou un nombre nu se tait devant le joueur.
        public static string Texte(string erreur, DocumentDuMonde document, TerresDeLaCarte terres, long cellule, long rang)
        {
            if (erreur != null || document == null) return string.Join("\n", LignesDuPays(terres, cellule, rang).Concat(LignesDuLieu(erreur, document, terres, cellule, rang)));
            try { return Decrire(document, terres, cellule, rang); }
            catch (ArgumentException e) { return string.Join("\n", LignesDuPays(terres, cellule, rang)) + "\nDossier incomplet : " + TexteDuMonde.Absence(e.Message, cellule.ToString(CultureInfo.InvariantCulture)); }
        }

        // La ligne du pays du lieu, d'après `/terres`, d'un seul tenant : son nom, puis son suzerain (« vassal de France ») ou, sans
        // suzerain, l'ensemble qu'il porte, puis ses habitants servis, ou leur absence. Un pays servi sans maison est une terre sans
        // État nommée, un lieu sans pays une terre qu'aucun pays ne tient : l'une et l'autre disent qu'on ne les joue pas, sans habitants.
        // Avant la lecture des terres, l'attente.
        public static List<string> LignesDuPays(TerresDeLaCarte terres, long cellule, long rang)
        {
            if (terres == null) return new List<string> { PAYS_EN_LECTURE };
            string pays = terres.PaysDuLieu(cellule, rang);
            if (pays == null) return new List<string> { SANS_ETAT + SEP + AUCUN_PAYS + SEP + ON_NE_LA_JOUE_PAS };
            string nom = terres.NomDuPays(pays) ?? PAYS_SANS_NOM;
            if (terres.MaisonDuPays(pays) == null) return new List<string> { SANS_ETAT + SEP + nom + SEP + ON_NE_LA_JOUE_PAS };
            var ligne = new StringBuilder(nom);
            string suzerain = terres.SuzerainDe(pays), ensemble = terres.EnsembleDe(pays);
            if (suzerain != null) ligne.Append(SEP).Append(NomsCourbes.Vassalite(terres.NomDuPays(suzerain)) ?? "vassal d'un pays sans nom");
            else if (ensemble != null) ligne.Append(SEP).Append(ensemble);
            ligne.Append(SEP).Append(terres.HabitantsDu(pays) is long n ? Habitants(n) : "habitants non servis");
            return new List<string> { ligne.ToString() };
        }

        // Les lignes du lieu, d'après `/lieu` : le lieu et ses habitants, sa province et les siens, puis le seigneur du lieu ; ou l'attente, ou la cause.
        // `terres` nomme les pays d'une province partagée ; nulles, la province ne nomme aucun pays.
        public static List<string> LignesDuLieu(string erreur, DocumentDuMonde document, TerresDeLaCarte terres, long cellule, long rang)
        {
            string id = cellule.ToString(CultureInfo.InvariantCulture);
            try { return erreur != null ? new List<string> { "Lecture indisponible : " + TexteDuMonde.Absence(erreur, id) } : document == null ? new List<string> { ATTENTE } : EnTete(document, terres, cellule, rang).lignes; }
            catch (ArgumentException e) { return new List<string> { "Dossier incomplet : " + TexteDuMonde.Absence(e.Message, id) }; }
        }

        // Les pays des lieux de la terre, d'après `/terres` : celui du bourg, puis ceux de ses autres lieux dans l'ordre servi, chacun une fois ;
        // un lieu sans maître compte comme tel. Vide sans terres lues.
        public static List<string> PaysDeLaProvince(TerresDeLaCarte terres, long cellule)
        {
            var noms = new List<string>(); if (terres == null) return noms;
            var vus = new HashSet<string>();
            void Ajouter(string pays) { if (vus.Add(pays ?? "")) noms.Add(pays == null ? LIEUX_SANS_MAITRE : terres.NomDuPays(pays) ?? PAYS_SANS_NOM); }
            Ajouter(terres.PaysDuLieu(cellule, 0));
            foreach (var lieu in terres.AutresPaysDe(cellule)) Ajouter(lieu.Pays);
            return noms;
        }

        // « A et B », « A, B et C ».
        static string Enumerer(IReadOnlyList<string> noms) => noms.Count == 1 ? noms[0] : string.Join(", ", noms.Take(noms.Count - 1)) + " et " + noms[noms.Count - 1];

        static string Nombre(double n) => n.ToString("0.##", CultureInfo.GetCultureInfo("fr-FR"));
        static string Habitants(long n) => TexteDuMonde.Nombre(n) + (n > 1 ? " habitants" : " habitant");
        static string Personnes(long n, string fait) => TexteDuMonde.Nombre(n) + (n > 1 ? " personnes " + fait + "s" : " personne " + fait);

        // Les trois lignes du lieu de ce rang et les lieux servis, dans l'ordre servi ; refuse une terre différente, des lieux absents ou répétés, un bourg ou un lieu manquant.
        // La province compte les habitants de toute la terre, tous pays confondus : quand ses lieux sont de plusieurs pays, elle les nomme.
        static (List<string> lignes, List<Dictionary<string, object>> lieux) EnTete(DocumentDuMonde document, TerresDeLaCarte terres, long cellule, long rang)
        {
            var racine = document.Champs;
            if (DocumentDuMonde.Entier(racine, "cell_id") != cellule) throw new ArgumentException("Territoire différent de la sélection");
            var lieux = DocumentDuMonde.Tableau(racine, "lieux").Select(l => l as Dictionary<string, object> ?? throw new ArgumentException("Lieu illisible")).ToList();
            if (lieux.Count == 0) throw new ArgumentException("Aucun lieu transmis");
            var rangs = new HashSet<long>();
            foreach (var l in lieux) if (!rangs.Add(DocumentDuMonde.Entier(l, "rang"))) throw new ArgumentException("Rang de lieu répété");
            var bourg = lieux.FirstOrDefault(l => DocumentDuMonde.Entier(l, "rang") == 0) ?? throw new ArgumentException("Bourg absent de la terre");
            var lieu = lieux.FirstOrDefault(l => DocumentDuMonde.Entier(l, "rang") == rang) ?? throw new ArgumentException("Lieu absent de la terre");
            var pays = PaysDeLaProvince(terres, cellule);
            var lignes = new List<string>
            {
                Nom(lieu) + " : " + Habitants(DocumentDuMonde.Entier(lieu, "population")) + " dans ce lieu",
                "Province " + De(Nom(bourg)) + (pays.Count > 1 ? SEP + "partagée : " + Enumerer(pays) : "") + SEP + Habitants(DocumentDuMonde.Entier(racine, "population")),
                Seigneur(racine, lieu),
            };
            return (lignes, lieux);
        }

        // « de » devant un nom, élidé devant une voyelle (« d'Avignon », « d'Évreux ») ; un nom qui porte déjà sa particule
        // (« de Basse Haie », « d'Armagnac ») la garde seule ; un nom qui commence par « Le » ou « Les » les contracte (« du Souf »,
        // « du Mans », « des Andelys »), un nom en « La » ou « L' » garde son article (« de La Rochelle », « de L'île de Jura »).
        public static string De(string nom)
        {
            if (nom.StartsWith("de ", StringComparison.Ordinal) || nom.StartsWith("d'", StringComparison.Ordinal) || nom.StartsWith("d’", StringComparison.Ordinal)) return nom;
            if (nom.StartsWith("Le ", StringComparison.Ordinal)) return "du " + nom.Substring(3);
            if (nom.StartsWith("Les ", StringComparison.Ordinal)) return "des " + nom.Substring(4);
            if (nom.StartsWith("La ", StringComparison.Ordinal) || nom.StartsWith("L'", StringComparison.Ordinal) || nom.StartsWith("L’", StringComparison.Ordinal)) return "de " + nom;
            return nom.Length > 0 && "aeiouyàâäéèêëîïôöûùüÿœ".IndexOf(char.ToLowerInvariant(nom[0])) >= 0 ? "d'" + nom : "de " + nom;
        }

        static string Nom(Dictionary<string, object> lieu) => DocumentDuMonde.Valeur(lieu, "nom") as string ?? "Nom du lieu non transmis";

        // La fiche lue : les lignes du pays et du lieu de ce rang, la date, puis chaque lieu par son nom, avec son pays quand ce n'est pas celui du bourg.
        public static string Decrire(DocumentDuMonde document, TerresDeLaCarte terres, long cellule, long rang)
        {
            var (lignes, lieux) = EnTete(document, terres, cellule, rang);
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

        // Le seigneur du lieu, selon la sorte que le dossier sert à sa maison : un seigneur plausible n'est pas une maison de l'histoire et
        // ne se nomme pas comme elle ; une grande maison ou une seigneurie se dit « maison » ; une autre sorte (une institution) se dit par
        // son nom seul. « Sans seigneur » pour un lieu sans maître ; une sorte ou un nom que le dossier ne sert pas se dit.
        static string Seigneur(Dictionary<string, object> racine, Dictionary<string, object> lieu)
        {
            var maitre = DocumentDuMonde.Valeur(lieu, "maitre");
            if (maitre == null) return "Sans seigneur";
            var maisons = DocumentDuMonde.Objet(DocumentDuMonde.Objet(racine, "noms"), "maisons");
            if (!(maitre is string id) || !maisons.TryGetValue(id, out var fiche)
                || !(fiche is Dictionary<string, object> maison)) return "Seigneur : nom non transmis";
            string sorte = maison.TryGetValue("sorte", out var s) ? s as string : null;
            if (sorte == SORTE_PLAUSIBLE) return SEIGNEUR_LOCAL;
            string nom = maison.TryGetValue("nom", out var n) && n is string texte ? texte : "nom non transmis";
            if (sorte == null) return "Seigneur : " + nom + ", sorte non transmise";
            return "Seigneur : " + (sorte == SORTE_GRANDE_MAISON || sorte == SORTE_SEIGNEURIE ? "maison " : "") + nom;
        }
    }
}
