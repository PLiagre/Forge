using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Les frontières de la carte au grain du lieu, photographiées quatre fois, chaque image partant de l'état de la précédente :
    //   1-france-et-voisins     la carte ouverte, la France choisie et « Commencer » pressé pour que l'accueil ne couvre plus la carte ; les terres servies
    //                           appliquées aux lieux (ceux de Pampelune d'un autre pays que sa cellule) ; la vue cadre les cellules de la France et un quart
    //                           de leur boîte de chaque côté ;
    //   2-italie                la boîte de Gênes, de Florence et de leurs voisines servies, élargie d'un dixième de chaque côté ;
    //   3-pyrenees-et-navarre   la boîte de la cellule de Pampelune et de ses voisines, élargie d'un dixième de chaque côté : une frontière passe à
    //                           l'intérieur de la cellule de Pampelune, partagée entre deux pays ;
    //   4-province-de-pres      la cellule de Pampelune seule, assez près pour que les traits de ses lieux se voient.
    // Le cadrage se fait par des cellules servies : la boîte d'une cellule est celle de ses contours servis, en km locaux de la carte. Chaque scénario
    // sonde une grille de points de l'écran, vérifie ce qu'il photographie et échoue sinon. Le tick est celui que le service sert, jamais un tick écrit
    // en dur. La toile du cabinet se pose devant la caméra de la carte à chaque scénario, au plan proche de la vue du moment.
    static class ScenarioFrontieresDesLieux
    {
        const string GROUPE = "frontieres-des-lieux", FRANCE = "France";
        const long PAMPELUNE = 10192, GENES = 10456, FLORENCE = 10260;
        static readonly long[] VOISINES_D_ITALIE = { 10256, 10446, 10447, 10454, 10466, 10265, 10267, 10268 }, VOISINES_DE_PAMPELUNE = { 10177, 10178, 10196, 10210 };
        const float MARGE_DE_LA_FRANCE = 0.25f, MARGE_AUTOUR = 0.1f;
        const float DEMI_DE_PRES_KM = 80f; // sous le seuil où le shader efface le bord des lieux, avec la marge d'une province
        const float KM_PAR_PIXEL_MAX = 0.35f; // au-delà, le shader efface le bord des lieux
        const float PROCHE_KM = 2f, VOISINAGE_KM = 4f, PAS_DE_LA_CELLULE_KM = 1f, TOLERANCE_DE_LA_BOITE_KM = 1f;
        const int COLONNES = 160, LIGNES = 90, IMAGES_DE_POSE = 4, POINTS_PRES_MIN = 5, RANGS_MIN = 5, CELLULES_MIN_DE_LA_FRANCE = 5;

        [ScenarioDeCapture(GROUPE, "1-france-et-voisins")]
        static IEnumerator FranceEtVoisins(Camera camera)
        {
            var e = ScenarioAccueil.OuvrirLaCarte(); while (e.MoveNext()) yield return e.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            // L'accueil couvre une part de la carte tant qu'aucun pays n'est choisi : la France est prise et « Commencer » pressé, comme le joueur.
            string france = guerre.Terres.Pays.Single(p => p.Nom == FRANCE).Id;
            cabinet.Accueil.Designer(guerre.Terres.Terres.First(t => t.Pays == france).CellId);
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Accueil.TexteDuNom == FRANCE && cabinet.Accueil.Montree != null && cabinet.Accueil.Commencer.interactable,
                () => "fiche de la France : « " + cabinet.Accueil.TexteDuNom + " » « " + cabinet.Accueil.TexteDeLaFiche + " »"); a.MoveNext();) yield return null;
            string maison = cabinet.Accueil.Montree.Id;
            var commencer = ScenarioAccueil.CommencerPuisLancer(cabinet); while (commencer.MoveNext()) yield return commencer.Current;
            for (var a = AttentesDeCapture.Jusqua(() => ScenarioAccueil.Servie(cabinet) == maison && cabinet.Partie.Jouable != null && cabinet.Partie.Maison?.Presente == true
                && !cabinet.Accueil.Ouvert && !cabinet.Accueil.Panneau.gameObject.activeSelf,
                () => "après « Commencer » : maison « " + ScenarioAccueil.Servie(cabinet) + " », reçu « " + (cabinet.Partie.Recu?.Erreur ?? cabinet.Partie.Recu?.Absence) + " », accueil ouvert " + cabinet.Accueil.Ouvert); a.MoveNext();) yield return null;
            // L'accueil se ferme dès le choix reçu, avant la maison servie : quelques images laissent le cabinet poser une fois la vue sur
            // le siège servi, pour que ce cadrage-là ne passe pas après celui du scénario.
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            // Les terres lues et appliquées aux lieux : ceux de Pampelune d'un autre pays que sa cellule portent le leur.
            var autres = guerre.Terres.AutresPaysDe(PAMPELUNE);
            if (autres.Count == 0) throw Faux("les terres servies ne donnent à la cellule " + PAMPELUNE + " aucun lieu d'un autre pays");
            for (var a = AttentesDeCapture.Jusqua(() => carte.PaysDe(PAMPELUNE) != null && autres.All(l => { string p = carte.PaysDuLieu(PAMPELUNE, l.Rang); return p != null && p != carte.PaysDe(PAMPELUNE); }),
                () => "les terres ne sont pas appliquées aux lieux de " + PAMPELUNE + " : pays de la cellule « " + carte.PaysDe(PAMPELUNE) + " », de son lieu " + autres[0].Rang + " « " + carte.PaysDuLieu(PAMPELUNE, autres[0].Rang) + " »"); a.MoveNext();) yield return null;
            // Les cellules dont le pays servi est la France.
            var cellules = carte.Lue.Cellules.Where(c => guerre.Terres.PaysDe(c.CellId) == france).Select(c => c.CellId).ToArray();
            if (cellules.Length < CELLULES_MIN_DE_LA_FRANCE) throw Faux("échantillon vide : " + cellules.Length + " cellules servies sont à « " + FRANCE + " »");
            var boite = Boite(carte, cellules);
            Vector2 centre = Cadrer(carte, cabinet, guerre, boite, MARGE_DE_LA_FRANCE, out float demi);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            VerifierQueLaBoiteTient(carte, boite, "la France");
            var (aTerre, pres, rangs) = Sonder(carte);
            VerifierUneFrontiere(carte, aTerre, pres);
            Debug.Log("CAPTURE frontières des lieux : la France et ses voisins au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + ", " + cellules.Length + " cellules, centre " + V(centre) + ", demi " + F(demi) + " km ; "
                + pres + " points près d'une frontière sur " + aTerre + " à terre ; " + autres.Count + " lieux de " + PAMPELUNE + " d'un autre pays ; rangs de " + PAMPELUNE + " vus : " + Rangs(rangs));
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "2-italie")]
        static IEnumerator Italie(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var cellules = new[] { GENES, FLORENCE }.Concat(VOISINES_D_ITALIE).ToArray();
            var boite = Boite(carte, cellules);
            Vector2 centre = Cadrer(carte, cabinet, guerre, boite, MARGE_AUTOUR, out float demi);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            VerifierQueLaBoiteTient(carte, boite, "l'Italie");
            var (aTerre, pres, rangs) = Sonder(carte);
            VerifierUneFrontiere(carte, aTerre, pres);
            Debug.Log("CAPTURE frontières des lieux : l'Italie au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + ", " + cellules.Length + " cellules, centre " + V(centre) + ", demi " + F(demi) + " km ; "
                + pres + " points près d'une frontière sur " + aTerre + " à terre ; rangs de " + PAMPELUNE + " vus : " + Rangs(rangs));
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "3-pyrenees-et-navarre")]
        static IEnumerator PyreneesEtNavarre(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var cellules = new[] { PAMPELUNE }.Concat(VOISINES_DE_PAMPELUNE).ToArray();
            var boite = Boite(carte, cellules);
            Vector2 centre = Cadrer(carte, cabinet, guerre, boite, MARGE_AUTOUR, out float demi);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            VerifierQueLaBoiteTient(carte, boite, "les Pyrénées et la Navarre");
            var (aTerre, pres, rangs) = Sonder(carte);
            VerifierUneFrontiere(carte, aTerre, pres);
            // Une frontière à l'intérieur de la cellule de Pampelune : un de ses points, près d'une frontière, dont les quatre voisins à quelques km restent dans la cellule.
            var (interieurs, exemple) = FrontieresDansLaCellule(carte, PAMPELUNE, boite[PAMPELUNE]);
            if (interieurs == 0) throw Faux("aucune frontière à l'intérieur de la cellule " + PAMPELUNE + " sous la vue (centre " + V(centre) + ", demi " + F(demi) + " km) : toute frontière proche en est le bord");
            Debug.Log("CAPTURE frontières des lieux : les Pyrénées et la Navarre au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + ", " + cellules.Length + " cellules, centre " + V(centre) + ", demi " + F(demi) + " km ; "
                + pres + " points près d'une frontière sur " + aTerre + " à terre ; " + interieurs + " points de la frontière à l'intérieur de " + PAMPELUNE + ", par exemple " + V(exemple) + " ; rangs de " + PAMPELUNE + " vus : " + Rangs(rangs));
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "4-province-de-pres")]
        static IEnumerator ProvinceDePres(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var boite = Boite(carte, new[] { PAMPELUNE });
            Vector2 centre = Cadrer(carte, cabinet, guerre, boite, 0f, out float demi, DEMI_DE_PRES_KM);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            var (aTerre, pres, rangs) = Sonder(carte);
            VerifierUneFrontiere(carte, aTerre, pres);
            if (rangs.Count < RANGS_MIN) throw Faux("la vue de près ne montre que " + rangs.Count + " lieux de la cellule " + PAMPELUNE + " (rangs " + Rangs(rangs) + "), il en faut " + RANGS_MIN);
            float kmParPixel = 2f * carte.Vue.Demi / carte.camera.pixelHeight;
            if (!(kmParPixel < KM_PAR_PIXEL_MAX)) throw Faux("la vue n'est pas assez près pour que le bord des lieux se voie : " + F(kmParPixel) + " km par pixel (demi " + F(carte.Vue.Demi) + " km, " + carte.camera.pixelHeight + " px), il en faut moins de " + F(KM_PAR_PIXEL_MAX));
            Debug.Log("CAPTURE frontières des lieux : la province de " + PAMPELUNE + " de près au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + ", centre " + V(centre) + ", demi " + F(carte.Vue.Demi) + " km (" + F(kmParPixel) + " km par pixel) ; "
                + pres + " points près d'une frontière sur " + aTerre + " à terre ; " + rangs.Count + " lieux de " + PAMPELUNE + " vus : " + Rangs(rangs));
            yield return carte.camera;
        }

        // La boîte de chaque cellule servie, en km locaux de la carte : celle de ses contours, converties comme le fait le dessin
        // (origine de la carte, mètres en km). Une cellule que le service ne sert pas, ou sans contour, fait échouer.
        sealed class Boites : Dictionary<long, (Vector2 min, Vector2 max)>
        {
            public (Vector2 min, Vector2 max) Union { get; set; }
        }

        static Boites Boite(CarteDessinee carte, IEnumerable<long> cellules)
        {
            PointCarte origine = carte.Origine ?? throw Faux("la carte posée n'a pas d'origine");
            var servies = carte.Lue.Cellules.ToDictionary(c => c.CellId);
            var boites = new Boites(); Vector2 tmin = new Vector2(float.PositiveInfinity, float.PositiveInfinity), tmax = new Vector2(float.NegativeInfinity, float.NegativeInfinity);
            foreach (long id in cellules)
            {
                if (!servies.TryGetValue(id, out CelluleDeCarte cellule)) throw Faux("la cellule " + id + " n'est pas servie");
                Vector2 min = new Vector2(float.PositiveInfinity, float.PositiveInfinity), max = new Vector2(float.NegativeInfinity, float.NegativeInfinity);
                foreach (var polygone in cellule.Contour)
                    foreach (PointCarte p in polygone.Exterieur)
                    {
                        var km = new Vector2((float)((p.X - origine.X) / 1000.0), (float)((p.Y - origine.Y) / 1000.0));
                        min = Vector2.Min(min, km); max = Vector2.Max(max, km);
                    }
                if (float.IsInfinity(min.x)) throw Faux("la cellule " + id + " n'a aucun contour servi");
                boites[id] = (min, max); tmin = Vector2.Min(tmin, min); tmax = Vector2.Max(tmax, max);
            }
            if (boites.Count == 0) throw Faux("aucune cellule à cadrer");
            boites.Union = (tmin, tmax);
            return boites;
        }

        // Pose la vue sur la boîte, élargie de `marge` de sa largeur et de sa hauteur de chaque côté : la demi-hauteur qui la fait tenir à l'écran
        // selon l'aspect de la caméra, ou `demiVoulue` quand on la donne. Puis la caméra, la toile et les noms suivent la vue.
        static Vector2 Cadrer(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre, Boites boite, float marge, out float demi, float? demiVoulue = null)
        {
            var (min, max) = boite.Union; Vector2 taille = max - min, centre = (min + max) / 2f;
            float aspect = carte.camera.aspect;
            demi = demiVoulue ?? Mathf.Max(taille.y * (1f + 2f * marge) / 2f, taille.x * (1f + 2f * marge) / 2f / aspect);
            demi = Mathf.Max(demi, VueDeCarte.DEMI_MIN_KM);
            carte.Vue.Changer(aspect); carte.Vue.Centrer(centre, demi); carte.Vue.Poser(carte.camera, carte.transform);
            PoserLaToile(carte, cabinet); guerre.SuivreLaVue();
            return carte.Vue.Centre;
        }

        // La boîte (sans la marge) tient dans ce que la vue montre.
        static void VerifierQueLaBoiteTient(CarteDessinee carte, Boites boite, string quoi)
        {
            var (min, max) = boite.Union; var vue = carte.Vue; float t = TOLERANCE_DE_LA_BOITE_KM;
            if (min.x < vue.Centre.x - vue.DemiLargeur - t || max.x > vue.Centre.x + vue.DemiLargeur + t || min.y < vue.Centre.y - vue.Demi - t || max.y > vue.Centre.y + vue.Demi + t)
                throw Faux("la boîte de " + quoi + " (" + V(min) + " à " + V(max) + ") ne tient pas dans la vue (centre " + V(vue.Centre) + ", demi " + F(vue.Demi) + " km, aspect " + F(vue.Aspect) + ")");
        }

        // Une grille de points de l'écran : combien sont à terre, combien à terre sont près d'une frontière, et les rangs de la cellule de Pampelune qu'on y voit.
        static (int aTerre, int pres, SortedSet<long> rangs) Sonder(CarteDessinee carte)
        {
            int aTerre = 0, pres = 0; var rangs = new SortedSet<long>();
            for (int j = 0; j < LIGNES; j++)
                for (int i = 0; i < COLONNES; i++)
                {
                    Vector2 km = carte.Vue.PointSous(new Vector2((i + .5f) / COLONNES, (j + .5f) / LIGNES));
                    var lieu = carte.LieuSous(Monde(carte, km));
                    if (lieu == null) continue;
                    aTerre++;
                    float distance = carte.DistanceALaFrontiere(km.x, km.y);
                    if (distance >= 0f && distance < PROCHE_KM) pres++;
                    if (lieu.Value.cellule.CellId == PAMPELUNE) rangs.Add(lieu.Value.rang);
                }
            return (aTerre, pres, rangs);
        }

        static void VerifierUneFrontiere(CarteDessinee carte, int aTerre, int pres)
        {
            if (aTerre == 0) throw Faux("aucune terre sous la vue (centre " + V(carte.Vue.Centre) + ", demi " + F(carte.Vue.Demi) + " km)");
            if (pres < POINTS_PRES_MIN) throw Faux("aucune frontière sous la vue (centre " + V(carte.Vue.Centre) + ", demi " + F(carte.Vue.Demi) + " km) : " + pres + " points sur " + aTerre
                + " à terre sont à moins de " + F(PROCHE_KM) + " km d'une frontière, il en faut " + POINTS_PRES_MIN);
        }

        // Les points de la cellule, vus à l'écran, à moins de PROCHE_KM d'une frontière et dont les quatre voisins à VOISINAGE_KM sont encore dans la cellule :
        // la frontière n'est alors pas le bord de la cellule. Le nombre de ces points, et l'un d'eux.
        static (int, Vector2) FrontieresDansLaCellule(CarteDessinee carte, long cellId, (Vector2 min, Vector2 max) boite)
        {
            var vue = carte.Vue; int n = 0; Vector2 exemple = default;
            bool Dedans(float x, float z) => carte.CelluleSous(Monde(carte, new Vector2(x, z)))?.CellId == cellId;
            for (float z = boite.min.y; z <= boite.max.y; z += PAS_DE_LA_CELLULE_KM)
                for (float x = boite.min.x; x <= boite.max.x; x += PAS_DE_LA_CELLULE_KM)
                {
                    if (Mathf.Abs(x - vue.Centre.x) > vue.DemiLargeur || Mathf.Abs(z - vue.Centre.y) > vue.Demi) continue;
                    var lieu = carte.LieuSous(Monde(carte, new Vector2(x, z)));
                    if (lieu == null || lieu.Value.cellule.CellId != cellId) continue;
                    float distance = carte.DistanceALaFrontiere(x, z);
                    if (distance < 0f || distance >= PROCHE_KM) continue;
                    if (!Dedans(x, z + VOISINAGE_KM) || !Dedans(x, z - VOISINAGE_KM) || !Dedans(x + VOISINAGE_KM, z) || !Dedans(x - VOISINAGE_KM, z)) continue;
                    if (n++ == 0) exemple = new Vector2(x, z);
                }
            return (n, exemple);
        }

        static Vector3 Monde(CarteDessinee carte, Vector2 km) => carte.transform.TransformPoint(new Vector3(km.x, 0f, km.y));

        // La toile du cabinet au plan proche courant de la caméra de la carte, qui suit la distance de la vue.
        static void PoserLaToile(CarteDessinee carte, CabinetDeCarte cabinet) =>
            cabinet.transform.Find("Cabinet").GetComponent<Canvas>().planeDistance = carte.camera.nearClipPlane + ScenarioAccueil.ECART_DE_PLAN;

        static string F(float v) => v.ToString("0.##", CultureInfo.InvariantCulture);
        static string V(Vector2 v) => "(" + v.x.ToString("0", CultureInfo.InvariantCulture) + ", " + v.y.ToString("0", CultureInfo.InvariantCulture) + ")";
        static string Rangs(IEnumerable<long> rangs) => "[" + string.Join(", ", rangs) + "]";

        static InvalidOperationException Faux(string raison) => new InvalidOperationException("frontières des lieux : " + raison);
    }
}
