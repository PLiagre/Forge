using System; using System.Collections.Generic; using System.Linq; using Forge.Pont; using UnityEngine; using UnityEngine.InputSystem; using UnityEngine.UI;

namespace Forge.Interface
{
    // Près du curseur, le lieu survolé comme Europa dit une province : son pays d'abord, sur une ligne (`/terres` : nom, suzerain ou ensemble,
    // habitants du pays ; ou la terre sans État qu'on ne joue pas), puis le lieu et ses habitants, sa province, les pays qui la partagent et ses
    // habitants, et son seigneur en dernier (`/lieu`), les lignes mêmes de la fiche (`DossierTerritoire`). LateUpdate suit SurvolDeCarte.
    // Puis, du registre `/modificateurs` lu au même tick, une ligne par modificateur du bourg et le total de chaque grandeur, tels que le monde les sert.
    public sealed class InfobulleDeTerre : MonoBehaviour
    {
        public const double PERIODE_S = 2; public const string CHEMIN_MODIFICATEURS = "/modificateurs"; public const string SANS_FIN = "tant que sa source tient";
        public bool automatique; public LectureDossier Lecture { get; set; } public LectureDossier LectureModificateurs { get; set; } public string TexteAffiche { get; private set; }
        // Les terres de `/terres`, nulles tant qu'elles ne sont pas lues.
        public Func<TerresDeLaCarte> Terres { get; set; }
        Canvas toile; Func<CelluleDeCarte> survolee; Func<long> rangSurvole; double prochaine, prochaineModificateurs; long? cellule, rangDit; DocumentDuMonde document, registre; TerresDeLaCarte terresDites; string erreur, erreurRegistre, texte;

        // La ligne du pays du lieu de ce rang, puis celles du lieu, de sa province et de son seigneur ; rien n'est compté ici.
        public static string Decrire(string erreur, DocumentDuMonde document, TerresDeLaCarte terres, long cellule, long rang)
            => string.Join("\n", DossierTerritoire.LignesDuPays(terres, cellule, rang).Concat(DossierTerritoire.LignesDuLieu(erreur, document, terres, cellule, rang)));

        // Les lignes du bourg (rang 0) de la terre, dans l'ordre servi : une par pose, puis le total de sa grandeur. Rien n'est additionné ici ; vide si le bourg n'a pas de pose.
        public static string[] DecrireModificateurs(DocumentDuMonde modificateurs, long cellule)
        {
            var dites = new List<string>();
            var bourg = DocumentDuMonde.Tableau(modificateurs.Champs, "lieux").Select(l => l as Dictionary<string, object> ?? throw new ArgumentException("Lieu illisible")).FirstOrDefault(l => DocumentDuMonde.Entier(l, "cell_id") == cellule && DocumentDuMonde.Entier(l, "rang") == 0);
            if (bourg == null) return dites.ToArray();
            foreach (var paire in DocumentDuMonde.Objet(bourg, "grandeurs"))
            {
                var grandeur = paire.Value as Dictionary<string, object> ?? throw new ArgumentException("Grandeur illisible : " + paire.Key); string nom = DocumentDuMonde.Texte(grandeur, "nom");
                foreach (Dictionary<string, object> ligne in DocumentDuMonde.Tableau(grandeur, "lignes").Select(l => l as Dictionary<string, object> ?? throw new ArgumentException("Ligne illisible : " + paire.Key)))
                {
                    object reste = DocumentDuMonde.Valeur(ligne, "reste_jours");
                    string duree = reste == null ? SANS_FIN : "encore " + TexteDuMonde.Jours(DocumentDuMonde.Entier(ligne, "reste_jours"));
                    dites.Add(nom + " : " + TexteDuMonde.Pourcentage(DocumentDuMonde.Nombre(ligne, "valeur")) + " " + DocumentDuMonde.Texte(ligne, "nom") + " · " + DocumentDuMonde.Texte(ligne, "source_dite") + " · " + duree);
                }
                dites.Add(nom + ", total : " + TexteDuMonde.Pourcentage(DocumentDuMonde.Nombre(grandeur, "total")));
            }
            return dites.ToArray();
        }

        // Le texte montré : les lignes du dossier, et celles des modificateurs seulement s'ils sont lus, sans faute, au tick de ce dossier ; sinon le texte du dossier seul, au caractère près.
        static string Montrer(string erreur, DocumentDuMonde dossier, TerresDeLaCarte terres, DocumentDuMonde registre, string erreurRegistre, long cellule, long rang)
        {
            string base3 = Decrire(erreur, dossier, terres, cellule, rang);
            if (erreur != null || dossier == null || registre == null || erreurRegistre != null || registre.Tick != dossier.Tick) return base3;
            try { var lignes = DecrireModificateurs(registre, cellule); return lignes.Length == 0 ? base3 : base3 + "\n" + string.Join("\n", lignes); }
            catch (ArgumentException faute) { Debug.LogWarning("InfobulleDeTerre : modificateurs illisibles, ignorés : " + faute.Message); return base3; }
        }

        // `rang` : le rang du lieu survolé dans sa terre (0, le bourg, s'il manque) ; `terres` : les terres de `/terres`.
        public void Initialiser(Canvas toile, LectureDossier lecture, Func<CelluleDeCarte> survolee, LectureDossier modificateurs = null, Func<long> rang = null, Func<TerresDeLaCarte> terres = null)
        { this.toile = toile; Lecture = lecture; LectureModificateurs = modificateurs; this.survolee = survolee; rangSurvole = rang; Terres = terres; }

        public void Pas(Vector2 point, CelluleDeCarte terre, double maintenant, long rang = 0)
        {
            if (terre == null)
            {
                var feuillet = TexteAffiche != null ? toile.transform.Find("Infobulle") : null;
                var ecrit = feuillet != null && feuillet.gameObject.activeInHierarchy ? feuillet.GetComponentInChildren<Text>(true) : null;
                if (ecrit != null && ecrit.text == TexteAffiche) Infobulle.Cacher(toile);
                TexteAffiche = null; return;
            }
            string chemin = "/lieu?cell=" + terre.CellId;
            if (!Lecture.EnCours && (Lecture.Cle != chemin || maintenant >= prochaine)) { _ = Lecture.Actualiser(chemin); prochaine = maintenant + PERIODE_S; }
            var modificateurs = LectureModificateurs;
            if (modificateurs != null && !modificateurs.EnCours && (modificateurs.Cle != CHEMIN_MODIFICATEURS || maintenant >= prochaineModificateurs)) { _ = modificateurs.Actualiser(CHEMIN_MODIFICATEURS); prochaineModificateurs = maintenant + PERIODE_S; }
            bool meme = Lecture.Cle == chemin; var lu = meme ? Lecture.Document : null; string faute = meme ? Lecture.Erreur : null;
            var registreLu = modificateurs?.Cle == CHEMIN_MODIFICATEURS ? modificateurs.Document : null; string fauteRegistre = modificateurs?.Cle == CHEMIN_MODIFICATEURS ? modificateurs.Erreur : null;
            var terres = Terres?.Invoke();
            if (cellule != terre.CellId || rangDit != rang || document != lu || erreur != faute || terresDites != terres || registre != registreLu || erreurRegistre != fauteRegistre)
            {
                cellule = terre.CellId; rangDit = rang; document = lu; erreur = faute; terresDites = terres; registre = registreLu; erreurRegistre = fauteRegistre;
                texte = Montrer(faute, lu, terres, registreLu, fauteRegistre, terre.CellId, rang);
            }
            TexteAffiche = texte; Infobulle.Montrer(toile, TexteAffiche, point);
        }

        void LateUpdate()
        {
            if (automatique || Mouse.current == null) return;
            var terre = survolee();
            Pas(Mouse.current.position.ReadValue(), terre, Time.realtimeSinceStartupAsDouble, terre != null && rangSurvole != null ? rangSurvole() : 0);
        }
    }
}
