using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class RepartitionHabitants
    {
        readonly Dictionary<long, long> populations = new Dictionary<long, long>();
        public long Minimum { get; }
        public long Maximum { get; }
        public string Legende { get; }
        public RepartitionHabitants(MondeLu monde)
        {
            if (monde == null || monde.Cellules.Count == 0 || monde.Cellules.Count != monde.CellCount)
                throw new ArgumentException("Population des territoires incomplète");
            foreach (var cellule in monde.Cellules)
            {
                if (cellule.Population < 0 || populations.ContainsKey(cellule.CellId))
                    throw new ArgumentException("Population négative ou territoire dupliqué");
                populations.Add(cellule.CellId, cellule.Population);
            }
            Minimum = populations.Values.Min(); Maximum = populations.Values.Max();
            string H(long n) => TexteDuMonde.Nombre(n) + (n < 2 ? " habitant" : " habitants");
            Legende = "Habitants : " + H(Minimum) + " (clair) → " + H(Maximum) + " (foncé) · échelle logarithmique · " + TexteDuMonde.Date(monde.Date);
        }
        public float Position(long cellId)
        {
            if (!populations.TryGetValue(cellId, out long nombre)) throw new ArgumentException("Population absente du territoire " + cellId);
            return Minimum == Maximum ? .5f : (float)(Math.Log(1d + nombre - Minimum) / Math.Log(1d + Maximum - Minimum));
        }
    }

    public enum ModeDeCarte { Puissances, Habitants, Flux }

    public sealed class CalquesCarte : MonoBehaviour
    {
        // Lot #963 : la bande des modes en bas à droite de la vue de la carte, sa légende juste au-dessus (unités de la toile, 1920 × 1080).
        public const string BANDE = "Modes de la carte", LEGENDE = "Légende du mode", COUPEE = "Calque indisponible : détail dans l'infobulle.";
        public const string FLUX = "Flux : ce que vos lieux envoient à votre siège, et votre siège à son suzerain, sur trente jours · Rouge : territoire conservé";
        public const int LIGNES_MAX = 3; const float X = 776, LARGEUR = 486, BAS = 1004, MARGE = 4;
        CarteDessinee carte;
        Func<MondeLu> monde;
        Func<CelluleDeCarte> selection;
        Dictionary<long, MeshRenderer> rendus;
        readonly Dictionary<long, (Material copie, Color maison)> teintes = new Dictionary<long, (Material, Color)>(); // couleur de la maison relevée une fois, jamais relue sur la copie teinte
        TextMesh[] noms;
        readonly List<Rect> etiquettes = new List<Rect>();
        Text legende; RectTransform fond; Infobulle bulle;
        MondeLu precedent;
        long? territoirePrecedent;
        bool changement = true;
        public ModeDeCarte Mode { get; private set; }
        public bool Habitants => Mode == ModeDeCarte.Habitants;
        public Text Legende => legende;
        public void Initialiser(CarteDessinee carte, Transform toile, Func<MondeLu> monde, Func<CelluleDeCarte> selection)
        {
            this.carte = carte; this.monde = monde; this.selection = selection;
            var bande = new GameObject(BANDE, typeof(RectTransform)).GetComponent<RectTransform>(); bande.SetParent(toile, false);
            bande.anchorMin = bande.anchorMax = bande.pivot = new Vector2(0, 1); bande.anchoredPosition = new Vector2(X, -1012); bande.sizeDelta = new Vector2(LARGEUR, SocleInterface.HauteurCommande);
            Bouton(bande, ModeDeCarte.Puissances, 0, "Colore la carte selon la maison qui tient chaque terre.");
            Bouton(bande, ModeDeCarte.Habitants, 165, "Colore la carte selon le nombre d'habitants de chaque terre.");
            Bouton(bande, ModeDeCarte.Flux, 330, "Passe les terres en papier pour lire ce que vos lieux envoient à votre siège, et votre siège à son suzerain.");
            var image = new GameObject(LEGENDE, typeof(RectTransform), typeof(Image)).GetComponent<Image>(); fond = image.rectTransform; fond.SetParent(toile, false);
            fond.anchorMin = fond.anchorMax = fond.pivot = new Vector2(0, 1); image.color = SocleInterface.Couleur("fond") * new Color(1f, 1f, 1f, .72f); image.raycastTarget = true; // pour l'infobulle
            bulle = fond.gameObject.AddComponent<Infobulle>(); legende = SocleInterface.Texte(fond, "Les calques attendent la carte…", 8, MARGE, LARGEUR - 16);
            legende.color = SocleInterface.Couleur("papier"); legende.supportRichText = false; legende.horizontalOverflow = HorizontalWrapMode.Wrap; legende.verticalOverflow = VerticalWrapMode.Overflow;
            Legender(legende.text, DetailDuMode(Mode));
        }
        void Bouton(Transform bande, ModeDeCarte mode, float x, string phrase)
        {
            var b = SocleInterface.Commande(bande, mode.ToString(), x, 0, () => { Mode = mode; changement = true; }, phrase: phrase); // un clic ne lit rien
            b.GetComponent<RectTransform>().sizeDelta = new Vector2(156, SocleInterface.HauteurCommande); var libelle = b.GetComponentInChildren<Text>().rectTransform; // à droite de l'icône
            libelle.anchoredPosition = new Vector2(36, 0); libelle.sizeDelta = new Vector2(120, SocleInterface.HauteurCommande);
        }
        public static Color Teinte(ModeDeCarte mode, bool retenue, Color maison, float position) => retenue ? SocleInterface.Couleur("alerte")
            : mode == ModeDeCarte.Habitants ? Color.Lerp(SocleInterface.Couleur("papier"), SocleInterface.Couleur("accent"), .65f * position)
            : mode == ModeDeCarte.Flux ? SocleInterface.Couleur("papier") : SocleInterface.Pigment(maison);
        public static string LegendeDuMode(ModeDeCarte mode, RepartitionHabitants repartition) => mode == ModeDeCarte.Flux ? FLUX
            : LegendeDuCalque(mode == ModeDeCarte.Puissances ? null : repartition ?? throw new ArgumentNullException(nameof(repartition), "légende des habitants sans répartition"));
        public static string DetailDuMode(ModeDeCarte mode) => (mode == ModeDeCarte.Habitants ? "Plus une terre est foncée, plus elle compte d'habitants. L'échelle est logarithmique : chaque pas de teinte multiplie les habitants au lieu de les additionner, pour que les petites terres restent lisibles à côté des grandes."
            : mode == ModeDeCarte.Flux ? "Toutes les terres passent en papier pour laisser lire les flèches : chacune part d'un de vos lieux vers votre siège, ou de votre siège vers celui de son suzerain, et s'épaissit avec ce qui est envoyé."
            : "Chaque terre porte, en pigment d'atlas, la couleur de la maison qui la tient : deux terres de même teinte ont le même maître.") + " Le rouge marque la terre que vous gardez ouverte.";
        // Les lignes que prendrait `contenu` dans `texte`, à sa largeur, la toile à l'échelle donnée ; à hauteur nulle, une troncature ne compterait rien.
        public static int Lignes(Text texte, string contenu, float echelle)
        {
            var reglages = texte.GetGenerationSettings(new Vector2(texte.rectTransform.rect.width, 0)); reglages.scaleFactor = echelle; reglages.verticalOverflow = VerticalWrapMode.Overflow;
            var generateur = new TextGenerator(); generateur.Populate(contenu, reglages); return generateur.lineCount;
        }
        public void Legender(string texte, string detail)
        {
            int lignes = Math.Max(Lignes(legende, texte, 1f), Lignes(legende, texte, 2f / 3f));
            if (lignes > LIGNES_MAX) throw new ArgumentException("légende de " + lignes + " lignes : trois au plus");
            Ecrire(texte, texte + "\n" + detail);
        }
        void Ecrire(string texte, string infobulle)
        {
            legende.text = texte; bulle.phrase = infobulle; float hauteur = legende.preferredHeight; legende.rectTransform.sizeDelta = new Vector2(LARGEUR - 16, hauteur);
            fond.sizeDelta = new Vector2(LARGEUR, hauteur + 2 * MARGE); fond.anchoredPosition = new Vector2(X, -(BAS - hauteur - 2 * MARGE)); // le bas reste à y 1004, sur la bande
        }
        void LateUpdate()
        {
            if (legende == null || carte.CellulesPosees == 0) return;
            EspacerLesNoms();
            var lu = monde(); long? retenu = selection()?.CellId;
            if (!changement && ReferenceEquals(lu, precedent) && retenu == territoirePrecedent) return;
            changement = false; precedent = lu; territoirePrecedent = retenu;
            try
            {
                if (rendus == null)
                {
                    var racine = carte.transform.Find("Cellules de la carte");
                    rendus = racine.GetComponentsInChildren<MeshRenderer>().ToDictionary(
                        r => long.Parse(r.name.Substring("Cellule ".Length), CultureInfo.InvariantCulture));
                    foreach (var r in rendus) { teintes.Add(r.Key, (new Material(r.Value.sharedMaterial), r.Value.sharedMaterial.color)); r.Value.sharedMaterial = teintes[r.Key].copie; }
                    carte.camera.backgroundColor = SocleInterface.Couleur("mer");
                    var police = SocleInterface.Police(titre: true);
                    noms = carte.GetComponentsInChildren<TextMesh>().OrderBy(n => n.text, StringComparer.Ordinal).ToArray();
                    foreach (var nom in noms)
                    {
                        nom.font = police; nom.fontSize = 16;
                        nom.GetComponent<MeshRenderer>().sharedMaterial = police.material;
                        nom.color = SocleInterface.Couleur("encre");
                    }
                }
                ModeDeCarte mode = Mode; bool habitants = mode == ModeDeCarte.Habitants;
                RepartitionHabitants repartition = habitants ? new RepartitionHabitants(lu) : null;
                if (habitants && rendus.Count != lu.Cellules.Count) throw new ArgumentException("Carte et populations ne couvrent pas les mêmes territoires");
                // Valider toutes les cellules avant de changer une seule couleur.
                if (habitants) foreach (long id in rendus.Keys) repartition.Position(id);
                foreach (var paire in rendus)
                {
                    paire.Value.SetPropertyBlock(null);
                    teintes[paire.Key].copie.color = Teinte(mode, paire.Key == retenu, teintes[paire.Key].maison, repartition?.Position(paire.Key) ?? 0f);
                }
                Legender(LegendeDuMode(mode, repartition), DetailDuMode(mode));
            }
            catch (Exception e)
            {
                if (rendus != null) foreach (var paire in rendus)
                {
                    paire.Value.SetPropertyBlock(null);
                    if (teintes.TryGetValue(paire.Key, out var t)) t.copie.color = paire.Key == retenu ? SocleInterface.Couleur("alerte") : SocleInterface.Pigment(t.maison);
                }
                string raison = Indisponible(e.Message), detail = DetailDuMode(ModeDeCarte.Puissances);
                try { Legender(raison, detail); }
                catch (ArgumentException) { Ecrire(COUPEE, raison + "\n" + detail); } // trop longue pour trois lignes : entière dans l'infobulle
            }
        }
        void OnDestroy() { foreach (var t in teintes.Values) if (Application.isPlaying) Destroy(t.copie); else DestroyImmediate(t.copie); teintes.Clear(); }

        // Lot #943 : sans année. Les couleurs des puissances sont relevées au dessin de la carte, jamais relues : les dater
        // dirait qu'elles sont celles du jour servi. La légende des habitants garde sa date, celle du monde lu.
        public static string LegendeDuCalque(RepartitionHabitants repartition) =>
            (repartition == null ? "Puissances de la carte · Relief non transmis" : repartition.Legende) + " · Rouge : territoire conservé";
        public static string Indisponible(string raison) => "Calque indisponible : " + TexteDuMonde.Absence(raison) + ". Couleurs des puissances conservées.";
        void EspacerLesNoms()
        {
            if (noms == null) return;
            etiquettes.Clear();
            foreach (var nom in noms)
            {
                var rendu = nom.GetComponent<MeshRenderer>();
                var bounds = rendu.bounds;
                var a = carte.camera.WorldToScreenPoint(bounds.min);
                var b = carte.camera.WorldToScreenPoint(bounds.max);
                var rect = Rect.MinMaxRect(Mathf.Min(a.x, b.x) - 3, Mathf.Min(a.y, b.y) - 2,
                    Mathf.Max(a.x, b.x) + 3, Mathf.Max(a.y, b.y) + 2);
                bool visible = carte.camera.pixelRect.Contains(rect.center) && !etiquettes.Any(r => r.Overlaps(rect));
                rendu.enabled = visible;
                if (visible) etiquettes.Add(rect);
            }
        }
    }
}
