using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Les villes que la carte sert, chacune une figurine posée sur le sol à sa place : un bourg, une ville dans ses
    // remparts ou une cité à tours, selon ses habitants servis, sur une échelle logarithmique entre la moins et la
    // plus peuplée des villes servies. Son socle est clair, bordé d'encre, comme le rond d'une ville sur un atlas, et
    // ses toits sont au cuivre du socle. Rien d'autre ne se lit dans la figurine : ni maître, ni richesse. De loin, une
    // figurine ne descend jamais sous `MIN_PX` pixels de large ; et le nom de la ville, posé par la carte, se range
    // juste au sud d'elle, à `MARGE_DU_NOM_PX` pixels de son socle. Quand la vue recule et que deux figurines se
    // recouvriraient à l'écran de plus de `RECOUVREMENT`, la moins peuplée des deux se cache, avec son nom, et
    // revient quand la vue s'approche. Sur la carte de la population, chaque figurine cède la place à un disque d'encre à la mesure de
    // ses habitants servis (`RayonDuDisque`).
    // La capitale de chaque pays qui tient une terre porte un socle à l'or vieilli, et ne descend jamais sous `MIN_PX_D_UNE_CAPITALE`. Elle se lit dans les réponses du monde :
    // la maison du pays (`/terres`) a son siège servi (`/jouables`, un nom et une cellule), qui est la ville de ce nom dans
    // cette cellule, ou la seule ville de ce nom sur la carte, sinon le siège de cette maison dans `/atlas`, où une figurine nommée est posée. Les capitales passent
    // avant les autres villes : une ville ne cache jamais une capitale ; et devant les noms des pays, qui s'écartent de leur emprise
    // (`EmprisesDesCapitales`). Un siège introuvable ne se devine pas : il se déclare.
    // Une figurine montrée répond au survol et au clic sur tout le sol qu'elle couvre, même là où elle déborde sur la mer : elle
    // ancre sur la carte le lieu de sa cellule (`CarteDessinee.Ancrer`), au rayon qu'elle a à l'écran.
    public sealed class VillesDeCarte : MonoBehaviour
    {
        public const string RACINE = "Figurines des villes", NOMS = "Villes de la carte", CAPITALES = "Capitales de l'atlas";
        public const float MIN_PX = 16f, MARGE_DU_NOM_PX = 11f, RECOUVREMENT = 0.25f;
        // Une capitale ne descend jamais sous `MIN_PX_D_UNE_CAPITALE` pixels : sa marque se lit de loin.
        public const float MIN_PX_D_UNE_CAPITALE = 24f;
        // De loin on lit les pays, de près les villes : au-delà de `KM_PAR_PIXEL_DES_VILLES` km par pixel au point visé, seules les
        // capitales se montrent ; les autres villes reviennent, avec leur nom, quand la vue s'approche.
        public const float KM_PAR_PIXEL_DES_VILLES = 1.6f;
        // La figurine d'un siège de l'atlas : ses habitants ne sont pas servis, elle prend la plus petite taille.
        public const int TAILLE_D_UN_SIEGE = 1;
        // Sur la carte de la population (`CalquesCarte.Mode`), chaque ville est un disque d'encre dont l'aire suit ses habitants servis,
        // à la même mesure pour toutes : `HABITANTS_PAR_KM2_DU_DISQUE` habitants par km² de disque, jamais sous `RAYON_MIN_DU_DISQUE_KM`
        // ni sous `MIN_PX_D_UN_DISQUE` pixels de large.
        public const double HABITANTS_PAR_KM2_DU_DISQUE = 500; public const float RAYON_MIN_DU_DISQUE_KM = 0.5f, MIN_PX_D_UN_DISQUE = 5f;
        public static float RayonDuDisque(long habitants) => Mathf.Max(RAYON_MIN_DU_DISQUE_KM, (float)Math.Sqrt(Math.Max(0, habitants) / HABITANTS_PAR_KM2_DU_DISQUE / Math.PI));
        // Les villes se montrent-elles en disques (la carte de la population), ou en figurines.
        public bool EnDisques { get; private set; }
        Mesh disque;
        CarteDessinee carte; Transform racine, racineDesCapitales; Material matiere; readonly Mesh[] formes = new Mesh[FormesDeCarte.TAILLE_MAX + 1], capitales = new Mesh[FormesDeCarte.TAILLE_MAX + 1];
        readonly List<Posee> posees = new List<Posee>(); readonly List<UnityEngine.Object> crees = new List<UnityEngine.Object>();
        Func<JouablesLus> jouables; CarteDeLaGuerre guerre; AtlasDeCarte atlas; string signature;
        readonly List<(string pays, string nom, string raison)> introuvables = new List<(string, string, string)>();
        sealed class Posee
        {
            public Transform Figurine, Nom; public Vector3 Pied; public int Taille; public long Habitants; public Vector2 Ecran; public float RayonPx, RayonKm; public bool Montree;
            public long CellId; public string Ville; public int Rang; public bool DeLAtlas; public readonly List<string> Pays = new List<string>();
            public bool Capitale => Pays.Count > 0;
        }

        public int Posees => posees.Count;
        // Chaque figurine posée : sa ville, son pied en km locaux, le rayon qu'elle couvre sur le sol, et si elle se montre.
        public IReadOnlyList<(string ville, Vector3 pied, float rayonKm, bool montree)> Figurines => posees.Select(p => (p.Ville, p.Pied, p.RayonKm, p.Montree)).ToList();
        public int Montrees { get; private set; }
        // Change quand des textes posés arrivent ou partent (les noms des sièges de l'atlas) : les calques les relèvent alors.
        public int VersionDesTextes { get; private set; }
        // Les capitales posées : le nom, la place en km locaux, les pays qui y tiennent leur siège, son texte posé et sa figurine.
        public IReadOnlyList<(string nom, Vector3 pied, IReadOnlyList<string> pays, TextMesh texte, Transform figurine)> Capitales =>
            posees.Where(p => p.Capitale).Select(p => (p.Ville, p.Pied, (IReadOnlyList<string>)p.Pays, p.Nom != null ? p.Nom.GetComponent<TextMesh>() : null, p.Figurine)).ToList();
        // Les pays tenants dont le siège ne se place pas, avec la raison.
        public IReadOnlyList<(string pays, string nom, string raison)> Introuvables => introuvables;
        public bool EstCapitale(TextMesh texte) => texte != null && posees.Any(p => p.Capitale && p.Nom == texte.transform);
        // Les places à l'écran, en pixels, des capitales montrées à la dernière image : leur figurine, et l'étiquette de leur nom au
        // sud d'elle, à la place et à la taille où les calques la posent (`CalquesCarte.EtiquetteDe`), montrée ou non. Un nom de pays
        // ne s'écrit pas dessus : la capitale passe devant lui.
        public IReadOnlyList<Rect> EmprisesDesCapitales => emprises;
        readonly List<Rect> emprises = new List<Rect>(); readonly Dictionary<Text, (string texte, int points, float largeur)> largeurs = new Dictionary<Text, (string, int, float)>(); CalquesCarte calques;
        // La phrase de la légende sur les sièges introuvables ; nulle quand toutes les capitales sont posées.
        public string TexteLegende => introuvables.Count == 0 ? null
            : "Capitales non placées, faute de siège servi sur la carte : " + introuvables.Count + " pays ("  + string.Join(", ", introuvables.Select(i => i.nom).Take(6)) + (introuvables.Count > 6 ? "…" : "") + ").";

        public void Installer() { carte = GetComponent<CarteDessinee>(); }
        // Les pays jouables (le siège de chaque maison), les pays des terres et l'atlas, d'où se lisent les capitales.
        public void Brancher(Func<JouablesLus> jouables, CarteDeLaGuerre guerre, AtlasDeCarte atlas) { this.jouables = jouables; this.guerre = guerre; this.atlas = atlas; signature = null; }
        void LateUpdate() => Pas();
        void OnDestroy() { if (carte != null) foreach (Posee p in posees) carte.Desancrer(p); foreach (var o in crees) Detruire(o); crees.Clear(); posees.Clear(); }

        // La taille de la figurine d'une ville de ce nombre d'habitants, de 1 à `TAILLE_MAX`, entre la moins et la plus
        // peuplée des villes servies, sur une échelle logarithmique ; celle du milieu quand toutes ont les mêmes habitants.
        public static int Taille(long habitants, long moins, long plus)
        {
            if (plus <= moins) return 2;
            // De combien de fois la ville dépasse la moins peuplée, rapporté à ce dont la plus peuplée la dépasse.
            double bas = Math.Max(1d, moins), place = Math.Log(Math.Max(1d, habitants) / bas) / Math.Log(Math.Max(1d, plus) / bas);
            return 1 + Math.Min(FormesDeCarte.TAILLE_MAX - 1, (int)(FormesDeCarte.TAILLE_MAX * Math.Min(1d, Math.Max(0d, place))));
        }

        // Pose les figurines une fois la carte posée, marque les capitales quand ce qui les dit change, puis règle tout sur la vue.
        public void Pas()
        {
            if (carte == null) return;
            if (racine == null) { if (carte.Lue == null || carte.CellulesPosees == 0) return; Poser(); }
            Capitaliser();
            if (calques == null) calques = GetComponent<CalquesCarte>();
            bool disques = calques != null && calques.Mode == ModeDeCarte.Population;
            if (disques != EnDisques) { EnDisques = disques; foreach (Posee p in posees) if (p.Figurine != null) p.Figurine.GetComponent<MeshFilter>().sharedMesh = disques ? Disque() : Forme(p.Taille, p.Capitale); }
            Camera camera = carte.camera; if (camera == null) return;
            foreach (Posee p in posees)
            {
                if (p.Figurine == null) continue;
                // Une figurine est faite en km à sa taille ; un disque a un km de rayon, et se grandit au rayon de ses habitants.
                Vector3 monde = carte.transform.TransformPoint(p.Pied); float rayon = disques ? RayonDuDisque(p.Habitants) : FormesDeCarte.RayonDuBourg(p.Taille);
                float echelle = FormesDeCarte.EchellePourLEcran(camera, monde, rayon, disques ? MIN_PX_D_UN_DISQUE : p.Capitale ? MIN_PX_D_UNE_CAPITALE : MIN_PX);
                p.Figurine.localScale = Vector3.one * echelle * (disques ? rayon : 1f); float kmParPixel = FormesDeCarte.KmParPixel(camera, monde);
                if (p.Nom != null) { float retrait = rayon * echelle + MARGE_DU_NOM_PX * kmParPixel; p.Nom.localPosition = carte.SurLeSol(p.Pied.x, p.Pied.z - retrait, CarteDessinee.HAUTEUR_NOM); }
                p.Ecran = camera.WorldToScreenPoint(monde); p.RayonKm = rayon * echelle; p.RayonPx = kmParPixel > 0f ? p.RayonKm / kmParPixel : 0f;
            }
            // Des capitales aux autres villes, puis de la plus peuplée à la moins peuplée : une figurine se montre si elle n'en recouvre aucune déjà montrée.
            // De trop loin, une ville qui n'est pas une capitale ne se montre pas.
            Montrees = 0; bool deLoin = VueDeLoin(camera);
            for (int k = 0; k < posees.Count; k++)
            {
                Posee p = posees[k]; if (p.Figurine == null) continue;
                bool libre = p.Capitale || !deLoin;
                for (int j = 0; j < k && libre; j++) { Posee q = posees[j]; if (q.Montree && (p.Ecran - q.Ecran).magnitude < (1f - RECOUVREMENT) * (p.RayonPx + q.RayonPx)) libre = false; }
                p.Montree = libre; if (libre) Montrees++;
                if (p.Figurine.gameObject.activeSelf != libre) p.Figurine.gameObject.SetActive(libre);
                if (p.Nom != null && p.Nom.gameObject.activeSelf != libre) p.Nom.gameObject.SetActive(libre);
                // La figurine montrée répond au survol et au clic sur tout ce qu'elle couvre, la mer comprise : son ancre tient
                // le lieu de sa cellule (d'un siège de l'atlas, celui sous son pied) ; cachée, elle ne couvre rien.
                carte.Ancrer(p, p.Pied, p.DeLAtlas ? (long?)null : p.CellId, libre ? p.RayonKm : 0f);
            }
            Emprises(camera);
        }

        // La figurine de chaque capitale montrée, et l'étiquette de son nom comme les calques la mesurent : sa largeur dite par la
        // police au corps posé, sa hauteur de 1,3 corps, et la même marge. Une étiquette pas encore posée n'a que sa figurine.
        void Emprises(Camera camera)
        {
            emprises.Clear(); if (calques == null) calques = GetComponent<CalquesCarte>();
            foreach (Posee p in posees)
            {
                if (!p.Capitale || !p.Montree || p.Figurine == null) continue;
                emprises.Add(new Rect(p.Ecran.x - p.RayonPx, p.Ecran.y - p.RayonPx, 2f * p.RayonPx, 2f * p.RayonPx));
                Text etiquette = p.Nom != null && calques != null ? calques.EtiquetteDe(p.Nom.GetComponent<TextMesh>()) : null; if (etiquette == null) continue;
                if (!largeurs.TryGetValue(etiquette, out var connue) || connue.texte != etiquette.text || connue.points != etiquette.fontSize) largeurs[etiquette] = connue = (etiquette.text, etiquette.fontSize, etiquette.preferredWidth);
                Vector3 ici = camera.WorldToScreenPoint(p.Nom.position); float hauteur = 1.3f * etiquette.fontSize;
                emprises.Add(new Rect(ici.x - connue.largeur / 2f - 3f, ici.y - hauteur / 2f - 2f, connue.largeur + 6f, hauteur + 4f));
            }
        }

        // La vue est-elle trop loin pour les villes : les km par pixel au milieu de l'écran, sur le sol.
        bool VueDeLoin(Camera camera)
        {
            // Le point visé : le milieu de l'écran sur le plan de la carte, mer comprise.
            Ray rayon = camera.ScreenPointToRay(camera.pixelRect.center); var plan = new Plane(carte.transform.up, carte.transform.position);
            if (!plan.Raycast(rayon, out float distance)) return false;
            return FormesDeCarte.KmParPixel(camera, rayon.GetPoint(distance)) > KM_PAR_PIXEL_DES_VILLES;
        }

        void Poser()
        {
            racine = new GameObject(RACINE).transform; racine.SetParent(transform, false); crees.Add(racine.gameObject);
            long moins = long.MaxValue, plus = long.MinValue;
            foreach (CelluleDeCarte cellule in carte.Lue.Cellules) foreach (VilleDeCarte ville in cellule.Villes) { moins = Math.Min(moins, ville.Population); plus = Math.Max(plus, ville.Population); }
            Transform noms = transform.Find(NOMS); int rang = 0;
            foreach (CelluleDeCarte cellule in carte.Lue.Cellules)
                foreach (VilleDeCarte ville in cellule.Villes)
                {
                    int taille = Taille(ville.Population, moins, plus); Vector3 pied = carte.PositionSurLaCarte(ville.Position, 0f).Value;
                    var objet = Figurine("Figurine de " + ville.Nom, pied, taille);
                    // Les noms de la carte sont posés dans le même ordre que ses villes.
                    Transform nom = noms != null && rang < noms.childCount && noms.GetChild(rang).name == "Ville " + ville.Nom ? noms.GetChild(rang) : null;
                    posees.Add(new Posee { Figurine = objet, Nom = nom, Pied = pied, Taille = taille, Habitants = ville.Population, CellId = cellule.CellId, Ville = ville.Nom, Rang = rang }); rang++;
                }
            Trier();
        }
        Transform Figurine(string nom, Vector3 pied, int taille)
        {
            var objet = new GameObject(nom, typeof(MeshFilter), typeof(MeshRenderer)); objet.transform.SetParent(racine, false); objet.transform.localPosition = pied;
            objet.GetComponent<MeshFilter>().sharedMesh = Forme(taille, false);
            var rendu = objet.GetComponent<MeshRenderer>(); rendu.sharedMaterial = Matiere(); rendu.shadowCastingMode = ShadowCastingMode.Off; rendu.receiveShadows = false;
            return objet.transform;
        }
        // Les capitales d'abord ; puis les plus peuplées ; à habitants égaux, dans l'ordre où la carte les sert.
        void Trier() => posees.Sort((a, b) => a.Capitale != b.Capitale ? b.Capitale.CompareTo(a.Capitale) : a.Habitants != b.Habitants ? b.Habitants.CompareTo(a.Habitants) : a.DeLAtlas != b.DeLAtlas ? a.DeLAtlas.CompareTo(b.DeLAtlas) : a.Rang.CompareTo(b.Rang));

        // Le siège de chaque pays tenant, lu dans ce que le monde sert ; refait seulement quand le résultat change.
        void Capitaliser()
        {
            TerresDeLaCarte terres = guerre?.Terres; if (terres == null) return;
            JouablesLus lus = jouables?.Invoke(); AtlasLu lu = atlas?.Atlas;
            // Tant que les jouables ou l'atlas sont en lecture, rien ne se décide : un siège n'est introuvable qu'une fois tout lu.
            if (lus == null || (atlas != null && lu == null && atlas.Absence == null)) return;
            var fiches = new Dictionary<string, FicheJouable>(); if (lus != null) foreach (var f in lus.Fiches) fiches[f.Id] = f;
            var sieges = new Dictionary<string, SiegeDeLAtlas>(); if (lu != null) foreach (var s in lu.Sieges) sieges[s.Maison] = s;
            var villes = new Dictionary<(long, string), Posee>(); var parNom = new Dictionary<string, Posee>(); var doubles = new HashSet<string>();
            foreach (Posee p in posees) if (!p.DeLAtlas) { villes[(p.CellId, p.Ville)] = p; if (!parNom.ContainsKey(p.Ville)) parNom[p.Ville] = p; else doubles.Add(p.Ville); }
            var tenants = new HashSet<string>(terres.Terres.Select(t => t.Pays).Where(p => p != null));
            var choix = new List<(string pays, Posee ville, SiegeDeLAtlas siege)>(); var absents = new List<(string, string, string)>();
            foreach (PaysDeLaCarte pays in terres.Pays.Where(p => tenants.Contains(p.Id)).OrderBy(p => p.Id, StringComparer.Ordinal))
            {
                string maison = pays.Maison?.Id, nom = pays.Nom ?? pays.Id;
                fiches.TryGetValue(maison ?? "", out FicheJouable fiche); SiegeJouable siege = fiche?.Siege;
                // La ville de ce nom dans la cellule du siège ; sinon la seule ville de ce nom sur la carte (le siège servi peut tenir à une cellule voisine de la ville).
                Posee ville = null;
                if (siege?.CellId is long cellule && siege.Nom != null && !villes.TryGetValue((cellule, siege.Nom), out ville) && !doubles.Contains(siege.Nom)) parNom.TryGetValue(siege.Nom, out ville);
                if (ville != null) choix.Add((pays.Id, ville, null));
                else if (maison != null && sieges.TryGetValue(maison, out SiegeDeLAtlas auSiege)) choix.Add((pays.Id, null, auSiege));
                else absents.Add((pays.Id, nom, maison == null ? "maison non servie" : fiche == null ? "maison sans siège servi"
                    : siege.CellId == null ? "siège hors de la carte" : lu == null ? "atlas non lu" : "siège « " + siege.Nom + " » ni ville de la carte ni siège de l'atlas"));
            }
            var sb = new StringBuilder(); foreach (var (p, v, s) in choix) sb.Append(p).Append('>').Append(v != null ? v.CellId + "/" + v.Ville : "atlas/" + s.Maison).Append(';');
            foreach (var a in absents) sb.Append('!').Append(a.Item1).Append(a.Item3);
            if (sb.ToString() == signature) return;
            signature = sb.ToString(); introuvables.Clear(); introuvables.AddRange(absents);
            // Les sièges de l'atlas d'avant partent ; les villes perdent leur marque.
            foreach (Posee p in posees.Where(p => p.DeLAtlas).ToList()) { posees.Remove(p); carte.Desancrer(p); Detruire(p.Figurine.gameObject); if (p.Nom != null) Detruire(p.Nom.gameObject); }
            foreach (Posee p in posees) p.Pays.Clear();
            if (racineDesCapitales == null) { racineDesCapitales = new GameObject(CAPITALES).transform; racineDesCapitales.SetParent(transform, false); crees.Add(racineDesCapitales.gameObject); }
            var deLAtlas = new Dictionary<string, Posee>(); int rang = posees.Count;
            foreach (var (p, v, s) in choix)
            {
                Posee ou = v;
                if (ou == null && !deLAtlas.TryGetValue(s.Maison, out ou))
                {
                    Vector3 pied = carte.PositionSurLaCarte(s.Point, 0f).Value;
                    var texte = new GameObject("Ville " + s.Nom).AddComponent<TextMesh>(); texte.transform.SetParent(racineDesCapitales, false); texte.text = s.Nom; texte.anchor = TextAnchor.MiddleCenter;
                    texte.transform.SetLocalPositionAndRotation(carte.SurLeSol(pied.x, pied.z, CarteDessinee.HAUTEUR_NOM), Quaternion.Euler(90, 0, 0));
                    ou = new Posee { Figurine = Figurine("Figurine de " + s.Nom, pied, TAILLE_D_UN_SIEGE), Nom = texte.transform, Pied = pied, Taille = TAILLE_D_UN_SIEGE, Habitants = 0, Ville = s.Nom, Rang = rang++, DeLAtlas = true };
                    posees.Add(ou); deLAtlas[s.Maison] = ou;
                }
                ou.Pays.Add(p);
            }
            foreach (Posee p in posees) if (p.Figurine != null) p.Figurine.GetComponent<MeshFilter>().sharedMesh = EnDisques ? Disque() : Forme(p.Taille, p.Capitale);
            Trier(); VersionDesTextes++;
        }

        // Le bourg d'une ville, aux toits de cuivre ; celui d'une capitale, aux toits rouge sang sur un socle à l'or vieilli, bordé d'encre.
        Mesh Forme(int taille, bool capitale)
        {
            Mesh[] table = capitale ? capitales : formes;
            if (table[taille] == null)
            {
                table[taille] = capitale
                    ? FormesDeCarte.Bourg(taille, SocleInterface.Couleur("papier"), SocleInterface.Couleur("encre"), SocleInterface.Couleur("sang"), SocleInterface.Couleur("or-vieilli"))
                    : FormesDeCarte.Bourg(taille, SocleInterface.Couleur("papier"), SocleInterface.Couleur("encre"), null, Color.Lerp(SocleInterface.Couleur("papier"), SocleInterface.Couleur("or"), .35f));
                if (capitale) table[taille].name = "Capitale de taille " + taille;
                crees.Add(table[taille]);
            }
            return table[taille];
        }
        // Le disque d'une ville sur la carte de la population : d'encre, bordé de papier, le même pour toutes.
        Mesh Disque() { if (disque == null) { disque = FormesDeCarte.Disque(SocleInterface.Couleur("encre"), SocleInterface.Couleur("papier")); crees.Add(disque); } return disque; }
        Material Matiere() { if (matiere == null) { matiere = FormesDeCarte.Matiere(SocleInterface.Couleur("cuivre")); matiere.name = RACINE; crees.Add(matiere); } return matiere; }
        static void Detruire(UnityEngine.Object o) { if (o == null) return; if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
    }
}
