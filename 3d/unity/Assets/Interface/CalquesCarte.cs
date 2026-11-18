using System;
using System.Collections.Generic;
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
        // La bande des modes en bas à droite de la vue de la carte, sa légende juste au-dessus (unités de la toile, 1920 × 1080).
        public const string BANDE = "Modes de la carte", LEGENDE = "Légende du mode", COUPEE = "Calque indisponible : détail dans l'infobulle.";
        public const string PUISSANCES = "Puissances de la carte · Rouge : territoire conservé", FLUX = "Orange : prélevé de chaque lieu vers votre siège · Violet : dû de votre siège à son suzerain · Sur trente jours · Rouge : territoire conservé";
        public const int LIGNES_MAX = 3; public const float FORCE_DU_LISERE = .55f; const float X = 776, LARGEUR = 486, BAS = 1004, MARGE = 4;
        // Le corps, en pixels sur un écran de 1080 de haut, d'un nom de ville et du nombre d'une armée : le même à toute
        // distance, jamais sous `POINTS_MIN`. Autour de l'encre, un liseré au papier du socle, large de `LISERE_PX`.
        public const float CORPS_DE_VILLE_PX = 17f, CORPS_DE_NOMBRE_PX = 19f, ECRAN_DE_REFERENCE_PX = 1080f, LISERE_PX = 1.2f, FORCE_DU_PAPIER = .85f;
        public const int POINTS_MIN = 9; public const string ETIQUETTES = "Étiquettes de la carte";
        CarteDessinee carte;
        Func<MondeLu> monde;
        Func<CelluleDeCarte> selection;
        Dictionary<long, Color> maisons; // la couleur de la maison de chaque terre dessinée, relevée une fois à la pose, jamais relue sur le terrain reteint
        Dictionary<long, string> departs; // le rattachement de chaque terre à la pose, relevé avec sa couleur : celui qui revient quand les pays ne sont pas lus
        TextMesh[] noms;
        // L'étiquette d'écran de chaque texte posé sur la carte, et la toile qui les porte, sur la caméra de la carte.
        readonly Dictionary<TextMesh, Text> ecrites = new Dictionary<TextMesh, Text>(); readonly Dictionary<Text, (string texte, int points, float largeur)> largeurs = new Dictionary<Text, (string, int, float)>();
        Canvas toileDesEtiquettes;
        readonly List<Rect> etiquettes = new List<Rect>();
        Text legende; RectTransform fond; Infobulle bulle;
        LieuxDeCarte lieux; FlechesDeCarte fleches; string ecrite, detaillee; RepartitionHabitants repartie; // la légende et le détail du dernier passage sans faute ; nuls après une faute
        CarteDeLaGuerre guerre; int versionDesPays = -1; // les pays servis des terres, et leur version au dernier passage
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
        public void Brancher(LieuxDeCarte lieux, FlechesDeCarte fleches, CarteDeLaGuerre guerre = null) { this.lieux = lieux; this.fleches = fleches; this.guerre = guerre; }
        void Bouton(Transform bande, ModeDeCarte mode, float x, string phrase)
        {
            var b = SocleInterface.Commande(bande, mode.ToString(), x, 0, () => { Mode = mode; changement = true; }, phrase: phrase); // un clic ne lit rien
            b.GetComponent<RectTransform>().sizeDelta = new Vector2(156, SocleInterface.HauteurCommande); var libelle = b.GetComponentInChildren<Text>().rectTransform; // à droite de l'icône
            libelle.anchoredPosition = new Vector2(36, 0); libelle.sizeDelta = new Vector2(120, SocleInterface.HauteurCommande);
        }
        public static Color Teinte(ModeDeCarte mode, bool retenue, Color maison, float position) => retenue ? SocleInterface.Couleur("alerte")
            : mode == ModeDeCarte.Habitants ? Color.Lerp(SocleInterface.Couleur("papier"), SocleInterface.Couleur("accent"), .65f * position)
            : mode == ModeDeCarte.Flux ? SocleInterface.Couleur("papier") : SocleInterface.Pigment(maison);
        // Le liseré d'un pays le long de sa frontière : son pigment, tiré vers l'encre pour se lire sur sa propre teinte comme sur le papier.
        public static Color Lisere(Color pays) => Color.Lerp(SocleInterface.Pigment(pays), SocleInterface.Couleur("encre"), FORCE_DU_LISERE);
        public static string LegendeDuMode(ModeDeCarte mode, RepartitionHabitants repartition) => mode == ModeDeCarte.Flux ? FLUX
            : LegendeDuCalque(mode == ModeDeCarte.Puissances ? null : repartition ?? throw new ArgumentNullException(nameof(repartition), "légende des habitants sans répartition"));
        public static string DetailDuMode(ModeDeCarte mode) => (mode == ModeDeCarte.Habitants ? "Plus une terre est foncée, plus elle compte d'habitants. L'échelle est logarithmique : chaque pas de teinte multiplie les habitants au lieu de les additionner, pour que les petites terres restent lisibles à côté des grandes."
            : mode == ModeDeCarte.Flux ? "Toutes les terres passent en papier pour laisser lire les flèches : chacune part d'un de vos lieux vers votre siège, ou de votre siège vers celui de son suzerain, et s'épaissit avec ce qui est envoyé."
            : "Chaque terre porte, en pigment d'atlas, la couleur de la maison qui la tient : deux terres de même teinte ont le même maître.") + " Le rouge marque la terre que vous gardez ouverte.";
        public static string LegendeDuMode(ModeDeCarte mode, RepartitionHabitants repartition, bool lieuxPeints) =>
            mode == ModeDeCarte.Puissances && lieuxPeints ? PUISSANCES + "\n" + LieuxDeCarte.ENTETE : LegendeDuMode(mode, repartition);
        // Les lieux parlent dans la légende des Puissances, les flèches dans celle du Flux ; l'infobulle ne reprend que les relevés des lieux, leur en-tête est déjà dans la légende.
        public static string DetailDuMode(ModeDeCarte mode, LieuxDeCarte lieux, FlechesDeCarte fleches) =>
            mode == ModeDeCarte.Puissances && lieux != null && lieux.Peint ? DetailDuMode(mode) + " Relief non transmis." + lieux.TexteLegende.Substring(LieuxDeCarte.ENTETE.Length)
            : mode == ModeDeCarte.Flux && fleches != null ? DetailDuMode(mode) + "\n" + fleches.TexteLegende : DetailDuMode(mode);
        // Les terres lues au pays servi : la légende des Puissances se date du jour lu ; sans terres lues, elle reste celle des puissances du départ.
        public const string PAYS = "Chaque terre porte, en pigment d'atlas, la couleur de son pays : la maison au sommet de la suzeraineté du maître de son bourg. Deux terres de même teinte sont du même pays ; une terre prise à un autre pays prend la teinte du preneur. Le rouge marque la terre que vous gardez ouverte.";
        public static string LegendeDesPays(TerresDeLaCarte terres) => "Pays au " + TexteDuMonde.Date(terres.Date) + " · Rouge : territoire conservé";
        public static string LegendeDuMode(ModeDeCarte mode, RepartitionHabitants repartition, bool lieuxPeints, CarteDeLaGuerre guerre) =>
            mode == ModeDeCarte.Puissances && guerre?.Terres != null ? LegendeDesPays(guerre.Terres) + (lieuxPeints ? "\n" + LieuxDeCarte.ENTETE : "") : LegendeDuMode(mode, repartition, lieuxPeints);
        // La guerre parle dans chaque mode : les armées et les frontières se voient partout.
        public static string DetailDuMode(ModeDeCarte mode, LieuxDeCarte lieux, FlechesDeCarte fleches, CarteDeLaGuerre guerre)
        {
            if (guerre == null) return DetailDuMode(mode, lieux, fleches);
            string detail = mode == ModeDeCarte.Puissances && guerre.Terres != null
                ? PAYS + (lieux != null && lieux.Peint ? lieux.TexteLegende.Substring(LieuxDeCarte.ENTETE.Length) : "") : DetailDuMode(mode, lieux, fleches);
            return detail + "\n" + guerre.TexteLegende;
        }
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
            // Les lieux et les flèches se lisent à leur rythme ; leur texte se récrit sans recolorer une terre. Après une faute, rien ne se récrit tant que rien ne bouge.
            int version = guerre != null ? guerre.Version : -1;
            if (!changement && ReferenceEquals(lu, precedent) && retenu == territoirePrecedent && version == versionDesPays) { if (ecrite != null) try { Recrire(repartie); } catch (ArgumentException) { changement = true; } return; }
            changement = false; precedent = lu; territoirePrecedent = retenu; versionDesPays = version; ecrite = null;
            try
            {
                if (maisons == null)
                {
                    maisons = new Dictionary<long, Color>(); departs = new Dictionary<long, string>();
                    foreach (var cellule in carte.Lue.Cellules) { Color? maison = carte.TeinteDe(cellule.CellId); if (maison.HasValue) { maisons.Add(cellule.CellId, maison.Value); departs.Add(cellule.CellId, carte.PaysDe(cellule.CellId)); } }
                    // La mer du terrain est celle du fond ; elle s'éclaircit un peu vers le papier au rivage, et les cimes tirent sur le papier.
                    Color mer = SocleInterface.Couleur("mer"), papier = SocleInterface.Couleur("papier");
                    carte.camera.backgroundColor = mer; carte.Habiller(mer, Color.Lerp(mer, papier, .11f), papier);
                    // Les traits du terrain à l'encre ; les lignes d'eau, une mer tirée vers le papier.
                    Color encre = SocleInterface.Couleur("encre"); carte.Encrer(encre, encre, encre, Color.Lerp(mer, papier, .45f));
                    var police = SocleInterface.Police(titre: true);
                    noms = carte.GetComponentsInChildren<TextMesh>().Where(n => guerre == null || !guerre.Possede(n.transform)).OrderBy(n => n.text, StringComparer.Ordinal).ToArray();
                    foreach (var nom in noms)
                    {
                        nom.font = police; nom.fontSize = 16;
                        nom.GetComponent<MeshRenderer>().sharedMaterial = police.material;
                        nom.color = SocleInterface.Couleur("encre");
                    }
                }
                ModeDeCarte mode = Mode; bool habitants = mode == ModeDeCarte.Habitants;
                RepartitionHabitants repartition = habitants ? new RepartitionHabitants(lu) : null;
                if (habitants && maisons.Count != lu.Cellules.Count) throw new ArgumentException("Carte et populations ne couvrent pas les mêmes territoires");
                // Valider toutes les cellules avant de changer une seule couleur.
                if (habitants) foreach (long id in maisons.Keys) repartition.Position(id);
                foreach (var paire in maisons)
                {
                    Color servie = guerre?.CouleurDe(paire.Key) ?? paire.Value; // le pays servi, sinon la puissance relevée au dessin
                    carte.Rattacher(paire.Key, guerre?.Terres != null ? guerre.Terres.PaysDe(paire.Key) : departs[paire.Key], Lisere(servie)); // la frontière suit le même pays que la teinte
                    carte.Teinter(paire.Key, Teinte(mode, paire.Key == retenu, servie, repartition?.Position(paire.Key) ?? 0f));
                }
                Recrire(repartition); repartie = repartition;
            }
            catch (Exception e)
            {
                ecrite = null;
                if (maisons != null) foreach (var paire in maisons)
                {
                    carte.Rattacher(paire.Key, departs[paire.Key], Lisere(paire.Value));
                    carte.Teinter(paire.Key, paire.Key == retenu ? SocleInterface.Couleur("alerte") : SocleInterface.Pigment(paire.Value));
                }
                string raison = Indisponible(e.Message), detail = DetailDuMode(ModeDeCarte.Puissances);
                try { Legender(raison, detail); }
                catch (ArgumentException) { Ecrire(COUPEE, raison + "\n" + detail); } // trop longue pour trois lignes : entière dans l'infobulle
            }
        }
        void Recrire(RepartitionHabitants repartition) { string texte = LegendeDuMode(Mode, repartition, lieux != null && lieux.Peint, guerre), detail = DetailDuMode(Mode, lieux, fleches, guerre); if (texte != ecrite || detail != detaillee || Mathf.Abs(legende.preferredHeight - legende.rectTransform.sizeDelta.y) > 1f /* la toile peut changer d'échelle */) { Legender(texte, detail); ecrite = texte; detaillee = detail; } }

        // Sans année. Les couleurs des puissances sont relevées au dessin de la carte, jamais relues : les dater
        // dirait qu'elles sont celles du jour servi. La légende des habitants garde sa date, celle du monde lu.
        public static string LegendeDuCalque(RepartitionHabitants repartition) =>
            (repartition == null ? "Puissances de la carte · Relief non transmis" : repartition.Legende) + " · Rouge : territoire conservé";
        public static string Indisponible(string raison) => "Calque indisponible : " + TexteDuMonde.Absence(raison) + ". Couleurs des puissances conservées.";
        // Un nom de ville ou le nombre d'une armée est un texte posé sur la carte, qui dit où il est et ce qu'il dit ; il se
        // lit sur une étiquette d'écran, au même corps quelle que soit la distance, nette et bordée d'un liseré clair, centrée
        // sur le point de l'écran où le texte se trouve. Le texte posé lui-même ne se dessine plus : couché sur le sol à une
        // taille en km, il devenait illisible sous une caméra inclinée. Son `enabled` dit toujours s'il est montré.
        // Les nombres des armées se montrent toujours ; puis les noms des villes, chacun seulement s'il ne recouvre rien de déjà montré.
        // Un nom de pays lisible réserve la place de chacune de ses lettres : un nom de ville ne s'écrit pas dessus, et revient
        // quand la vue s'approche et que le nom du pays s'efface.
        void EspacerLesNoms()
        {
            if (noms == null) return;
            etiquettes.Clear();
            // Un texte retiré de la carte emporte son étiquette.
            if (ecrites.Keys.Any(texte => texte == null))
            {
                var gardees = ecrites.Where(p => p.Key != null).ToList(); foreach (var paire in ecrites) if (paire.Key == null && paire.Value != null) { largeurs.Remove(paire.Value); Detruire(paire.Value.gameObject); }
                ecrites.Clear(); foreach (var paire in gardees) ecrites.Add(paire.Key, paire.Value);
            }
            if (toileDesEtiquettes != null && carte.camera != null) toileDesEtiquettes.planeDistance = carte.camera.nearClipPlane * 1.5f;
            if (guerre != null) { foreach (var nombre in guerre.NombresDesArmees) Espacer(nombre, true, CORPS_DE_NOMBRE_PX); guerre.Ecriture?.Reserver(carte.camera, etiquettes); }
            foreach (var nom in noms) Espacer(nom, false, CORPS_DE_VILLE_PX);
        }
        // L'étiquette d'écran d'un texte posé sur la carte ; null tant qu'il n'a pas été présenté.
        public Text EtiquetteDe(TextMesh nom) => nom != null && ecrites.TryGetValue(nom, out Text texte) ? texte : null;
        Text Etiqueter(TextMesh nom)
        {
            if (ecrites.TryGetValue(nom, out Text deja) && deja != null) return deja;
            if (toileDesEtiquettes == null)
            {
                // Sur la caméra de la carte, juste derrière son plan proche : une capture de cette caméra voit les étiquettes.
                // La toile n'est pas un enfant direct de la carte : le cabinet éteint toute toile qui l'est, hors la sienne.
                Transform porte = new GameObject(ETIQUETTES).transform; porte.SetParent(carte.transform, false);
                toileDesEtiquettes = new GameObject("Toile des étiquettes", typeof(RectTransform)).AddComponent<Canvas>(); toileDesEtiquettes.transform.SetParent(porte, false);
                toileDesEtiquettes.renderMode = RenderMode.ScreenSpaceCamera; toileDesEtiquettes.worldCamera = carte.camera; toileDesEtiquettes.sortingOrder = -1;
            }
            var texte = new GameObject(nom.name, typeof(RectTransform)).AddComponent<Text>(); texte.transform.SetParent(toileDesEtiquettes.transform, false);
            texte.font = SocleInterface.Police(titre: true); texte.color = SocleInterface.Couleur("encre"); texte.alignment = TextAnchor.MiddleCenter; texte.raycastTarget = false; texte.supportRichText = false;
            texte.horizontalOverflow = HorizontalWrapMode.Overflow; texte.verticalOverflow = VerticalWrapMode.Overflow;
            var cadre = texte.rectTransform; cadre.anchorMin = cadre.anchorMax = Vector2.zero; cadre.pivot = new Vector2(.5f, .5f); cadre.sizeDelta = Vector2.zero;
            var lisere = texte.gameObject.AddComponent<Outline>(); Color papier = SocleInterface.Couleur("papier"); papier.a = FORCE_DU_PAPIER; lisere.effectColor = papier; lisere.effectDistance = new Vector2(LISERE_PX, -LISERE_PX);
            ecrites[nom] = texte; return texte;
        }
        float Largeur(Text texte)
        {
            if (largeurs.TryGetValue(texte, out var connue) && connue.texte == texte.text && connue.points == texte.fontSize) return connue.largeur;
            float largeur = texte.preferredWidth; largeurs[texte] = (texte.text, texte.fontSize, largeur); return largeur;
        }
        static void Detruire(UnityEngine.Object o) { if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
        void Espacer(TextMesh nom, bool toujours, float corpsPx)
        {
            if (nom == null) return;
            Camera camera = carte.camera; var rendu = nom.GetComponent<MeshRenderer>(); rendu.forceRenderingOff = true; Text texte = Etiqueter(nom);
            // Un texte posé qu'on a éteint (une ville cachée derrière une plus grande) n'a pas d'étiquette.
            if (!nom.gameObject.activeInHierarchy) { rendu.enabled = false; texte.enabled = false; return; }
            int points = Mathf.Max(POINTS_MIN, Mathf.RoundToInt(corpsPx * camera.pixelHeight / ECRAN_DE_REFERENCE_PX));
            if (texte.text != nom.text) texte.text = nom.text; if (texte.fontSize != points) texte.fontSize = points;
            Vector3 ecran = camera.WorldToScreenPoint(nom.transform.position); float largeur = Largeur(texte), hauteur = 1.3f * points;
            var rect = new Rect(ecran.x - largeur / 2f - 3f, ecran.y - hauteur / 2f - 2f, largeur + 6f, hauteur + 4f);
            // Derrière la caméra, rien ne se montre.
            bool visible = ecran.z > camera.nearClipPlane && (toujours || camera.pixelRect.Contains(rect.center) && !etiquettes.Any(r => r.Overlaps(rect)));
            rendu.enabled = visible; texte.enabled = visible;
            if (!visible) return;
            etiquettes.Add(rect); texte.rectTransform.anchoredPosition = (Vector2)ecran - camera.pixelRect.min;
        }
    }
}
