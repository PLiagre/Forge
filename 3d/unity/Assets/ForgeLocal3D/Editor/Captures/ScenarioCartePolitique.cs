using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // La carte politique de 1400, photographiée six fois contre le vrai service, à poser à côté d'un atlas de 1400 et de la carte
    // politique d'Europa Universalis IV : l'Europe entière, la France et les Îles, l'Empire, l'Italie, les Balkans et l'Orient,
    // le Maghreb avec le Zab. Chaque cadre se calcule sur les terres servies des pays qu'il montre, jamais sur des coordonnées
    // écrites en dur. Chaque photo vérifie ce qu'elle montre et échoue sinon : les grands pays du cadre, ceux qui tiennent au
    // moins `TERRES_D_UN_GRAND_PAYS` terres, ont leur nom lisible et leur capitale marquée quand le monde sert son siège ; un nom
    // de l'atlas au moins s'y lit ; deux pays voisins dans le cadre n'ont pas la même couleur. Aucun nom de pays écrit n'est
    // celui d'une dynastie servie. Le Zab montre Biskra marquée et nommée. La toile du cabinet n'est pas photographiée : la
    // caméra de la carte, sur toute l'image, voit la carte et ses étiquettes, sur un écran de la taille de la photo.
    static class ScenarioCartePolitique
    {
        const int TERRES_D_UN_GRAND_PAYS = 5, PAYS_DE_L_EUROPE = 5, IMAGES_DE_POSE = 12;
        const float MARGE_DU_CADRE = 1.06f, ASPECT = 1600f / 900f, ECART_AU_GROS = 1.6f;

        [ScenarioDeCapture("carte-politique", "1-europe")]
        static IEnumerator Europe(Camera camera)
        {
            var e = Ouvrir(); while (e.MoveNext()) yield return e.Current;
            var (carte, guerre, _, _, _) = Lire();
            ScenarioAccueil.VerifierLesNoms(guerre);
            // L'Europe entière : toutes les terres servies ; les cinq pays qui tiennent le plus de terres doivent s'y lire.
            var grands = guerre.Terres.Terres.Where(t => t.Pays != null).GroupBy(t => t.Pays).OrderByDescending(g => g.Count()).ThenBy(g => g.Key, StringComparer.Ordinal).Take(PAYS_DE_L_EUROPE).Select(g => g.Key).ToList();
            var p = Photographier("europe", TerresDuCadre(guerre, "europe"), grands); while (p.MoveNext()) yield return p.Current;
        }

        [ScenarioDeCapture("carte-politique", "2-france-et-iles")]
        static IEnumerator FranceEtIles(Camera camera)
        {
            var (_, guerre, _, _, _) = Lire();
            var p = Photographier("france-et-iles", TerresDuCadre(guerre, "france-et-iles")); while (p.MoveNext()) yield return p.Current;
        }

        [ScenarioDeCapture("carte-politique", "3-empire")]
        static IEnumerator Empire(Camera camera)
        {
            var (_, guerre, _, _, _) = Lire();
            var p = Photographier("empire", TerresDuCadre(guerre, "empire")); while (p.MoveNext()) yield return p.Current;
        }

        [ScenarioDeCapture("carte-politique", "4-italie")]
        static IEnumerator Italie(Camera camera)
        {
            var (_, guerre, _, _, _) = Lire();
            var p = Photographier("italie", TerresDuCadre(guerre, "italie")); while (p.MoveNext()) yield return p.Current;
        }

        [ScenarioDeCapture("carte-politique", "5-balkans-et-orient")]
        static IEnumerator BalkansEtOrient(Camera camera)
        {
            var (_, guerre, _, _, _) = Lire();
            var p = Photographier("balkans-et-orient", TerresDuCadre(guerre, "balkans-et-orient")); while (p.MoveNext()) yield return p.Current;
        }

        // Les terres servies que montre chaque cadre de la carte politique, d'après les pays servis ; la planche de l'atlas
        // cadre les mêmes.
        internal static readonly string[] CADRES = { "europe", "france-et-iles", "empire", "italie", "balkans-et-orient" };
        internal static List<long> TerresDuCadre(CarteDeLaGuerre guerre, string cadre)
        {
            List<string> montres;
            switch (cadre)
            {
                case "europe": return guerre.Terres.Terres.Select(t => t.CellId).ToList();
                case "france-et-iles":
                    // La France et tous ceux qui relèvent d'elle, l'Angleterre et la Guyenne, l'Écosse, l'Irlande.
                    string france = Pays(guerre, "France");
                    montres = guerre.Terres.Pays.Where(x => guerre.Couleurs.Racine(x.Id) == france).Select(x => x.Id).Concat(new[] { "Angleterre", "Écosse", "Irlande" }.Select(n => Pays(guerre, n))).ToList();
                    montres.AddRange(guerre.Terres.Pays.Where(x => montres.Contains(x.Suzerain)).Select(x => x.Id));
                    break;
                case "empire":
                    montres = guerre.Terres.Pays.Where(x => x.Ensemble == "Saint-Empire").Select(x => x.Id).ToList();
                    if (montres.Count == 0) throw Faux("aucun pays servi n'est de l'ensemble « Saint-Empire »");
                    break;
                case "italie": montres = new[] { "Milan", "Venise", "Gênes", "Florence", "États de l'Église", "Naples", "Sicile", "Savoie" }.Select(n => Pays(guerre, n)).ToList(); break;
                case "balkans-et-orient":
                    // Les Ottomans et ceux qui relèvent d'eux, Byzance et la Morée, la Serbie, la Bosnie, la Valachie, la Moldavie.
                    montres = new[] { "Ottomans", "Byzance", "Bosnie", "Valachie", "Moldavie" }.Select(n => Pays(guerre, n)).ToList();
                    montres.AddRange(guerre.Terres.Pays.Where(x => montres.Contains(x.Suzerain)).Select(x => x.Id));
                    break;
                default: throw Faux("cadre inconnu : " + cadre);
            }
            return Terres(guerre, montres).ToList();
        }

        // Le cadre de la vue sur des terres, pour une image de cet aspect : le gros des terres, sans qu'une terre lointaine (Caffa,
        // que tient Gênes) n'élargisse le cadre. Une terre est gardée à moins de `ECART_AU_GROS` fois la distance qui laisse les
        // quatre cinquièmes des terres autour du centre médian.
        internal static (Vector2 centre, float demi) Cadrer(CarteDessinee carte, IEnumerable<long> terres, float aspect)
        {
            var cadrees = new HashSet<long>(terres);
            Vector2 Centre(CelluleDeCarte c) { Vector3 v = carte.PositionSurLaCarte(c.Contour[0].Exterieur[0], 0f).Value; return new Vector2(v.x, v.z); }
            var choisies = carte.Lue.Cellules.Where(c => cadrees.Contains(c.CellId)).ToList();
            if (choisies.Count == 0) throw Faux("aucune terre à cadrer");
            var xs = choisies.Select(c => Centre(c).x).OrderBy(x => x).ToList(); var zs = choisies.Select(c => Centre(c).y).OrderBy(z => z).ToList();
            var median = new Vector2(xs[xs.Count / 2], zs[zs.Count / 2]); var distances = choisies.Select(c => (Centre(c) - median).magnitude).OrderBy(d => d).ToList();
            float portee = ECART_AU_GROS * distances[Mathf.Min(distances.Count - 1, (int)(0.8f * distances.Count))] + 1f;
            float minX = float.MaxValue, minZ = float.MaxValue, maxX = float.MinValue, maxZ = float.MinValue;
            foreach (CelluleDeCarte cellule in choisies.Where(c => (Centre(c) - median).magnitude <= portee))
                foreach (PolygoneDeCarte polygone in cellule.Contour)
                    foreach (PointCarte point in polygone.Exterieur)
                        if (carte.PositionSurLaCarte(point, 0f) is Vector3 v) { minX = Mathf.Min(minX, v.x); maxX = Mathf.Max(maxX, v.x); minZ = Mathf.Min(minZ, v.z); maxZ = Mathf.Max(maxZ, v.z); }
            return (new Vector2((minX + maxX) / 2f, (minZ + maxZ) / 2f), Mathf.Max((maxZ - minZ) / 2f, (maxX - minX) / 2f / aspect) * MARGE_DU_CADRE);
        }

        [ScenarioDeCapture("carte-politique", "6-maghreb-et-zab")]
        static IEnumerator MaghrebEtZab(Camera camera)
        {
            var (carte, guerre, villes, calques, _) = Lire();
            string zab = Pays(guerre, "Émirat du Zab");
            var montres = new[] { "Hafsides", "Zayyanides", "Mérinides" }.Select(n => Pays(guerre, n)).Concat(new[] { zab }).ToList();
            var p = Photographier("maghreb-et-zab", Terres(guerre, montres)); while (p.MoveNext()) yield return p.Current;
        }

        // La carte ouverte, dessinée, ses pays coloriés et nommés, l'atlas posé et les capitales marquées.
        static IEnumerator Ouvrir()
        {
            SceneManager.LoadScene(OuvertureDeLaCarte.SCENE);
            yield return null;
            CarteDessinee carte = null; CarteDeLaGuerre guerre = null; AtlasDeCarte atlas = null; VillesDeCarte villes = null;
            for (var a = AttentesDeCapture.Jusqua(() => (carte = Object.FindFirstObjectByType<CarteDessinee>()) != null && carte.Vue != null && carte.camera != null
                && (guerre = carte.GetComponent<CarteDeLaGuerre>()) != null && guerre.Terres != null && guerre.Couleurs != null && guerre.NomsDesPays.Count > 0
                && (atlas = carte.GetComponent<AtlasDeCarte>()) != null && atlas.Ecriture != null && (villes = carte.GetComponent<VillesDeCarte>()) != null && villes.Capitales.Count > 0,
                () => "carte politique non prête (" + (guerre?.AbsenceDesTerres ?? atlas?.Absence ?? (villes == null ? "pas de villes" : "capitales " + villes.Capitales.Count)) + ")"); a.MoveNext();) yield return null;
            // Sans écran, la vue du jeu est petite : les noms s'y règleraient pour elle. La caméra de la carte rend dans un écran
            // de la taille de la photo, proche de celui du jeu, et les noms, les étiquettes et les figurines s'y règlent.
            if (carte.camera.targetTexture == null) carte.camera.targetTexture = new RenderTexture(1600, 900, 24) { name = "Écran de la carte politique" };
        }

        static (CarteDessinee, CarteDeLaGuerre, VillesDeCarte, CalquesCarte, AtlasDeCarte) Lire()
        {
            var carte = Object.FindFirstObjectByType<CarteDessinee>() ?? throw Faux("pas de carte");
            var guerre = carte.GetComponent<CarteDeLaGuerre>(); var villes = carte.GetComponent<VillesDeCarte>(); var calques = carte.GetComponent<CalquesCarte>(); var atlas = carte.GetComponent<AtlasDeCarte>();
            if (guerre?.Terres == null || villes == null || calques == null || atlas?.Ecriture == null) throw Faux("la carte politique n'est pas ouverte : « 1-europe » n'a pas réussi");
            return (carte, guerre, villes, calques, atlas);
        }

        static string Pays(CarteDeLaGuerre guerre, string nom) => guerre.Terres.Pays.SingleOrDefault(p => p.Nom == nom)?.Id ?? throw Faux("aucun pays servi ne s'appelle « " + nom + " »");
        static IEnumerable<long> Terres(CarteDeLaGuerre guerre, ICollection<string> pays) => guerre.Terres.Terres.Where(t => t.Pays != null && pays.Contains(t.Pays)).Select(t => t.CellId);

        // Cadre la vue sur les terres données, laisse la carte se régler, vérifie ce qu'elle montre, puis rend la caméra à photographier.
        // `grands` : les pays dont le nom doit se lire ; par défaut, ceux du cadre qui tiennent au moins `TERRES_D_UN_GRAND_PAYS` terres.
        static IEnumerator Photographier(string cadre, IEnumerable<long> terres, IList<string> grands = null)
        {
            var (carte, guerre, villes, calques, atlas) = Lire();
            var cadrees = new HashSet<long>(terres); if (cadrees.Count == 0) throw Faux(cadre + " : aucune terre à cadrer");
            var (centre, demi) = Cadrer(carte, cadrees, ASPECT);
            carte.camera.rect = new Rect(0, 0, 1, 1); carte.camera.aspect = ASPECT;
            carte.Vue.Changer(ASPECT); carte.Vue.Centrer(centre, demi); carte.Vue.Poser(carte.camera, carte.transform);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Camera cam = carte.camera;
            bool Dans(long cellId) { var c = carte.Lue.Cellules.First(x => x.CellId == cellId); Vector3 v = cam.WorldToViewportPoint(carte.transform.TransformPoint(carte.PositionSurLaCarte(c.Contour[0].Exterieur[0], 0f).Value)); return v.z > 0f && v.x >= 0f && v.x <= 1f && v.y >= 0f && v.y <= 1f; }
            // Les grands pays du cadre : leur nom se lit, leur capitale est marquée quand le monde sert son siège.
            grands = grands ?? guerre.Terres.Terres.Where(t => t.Pays != null && cadrees.Contains(t.CellId)).GroupBy(t => t.Pays).Where(g => g.Count() >= TERRES_D_UN_GRAND_PAYS).Select(g => g.Key).ToList();
            if (grands.Count == 0) throw Faux(cadre + " : aucun grand pays dans le cadre");
            var noms = guerre.NomsDesPays.ToDictionary(n => n.Pays);
            string illisibles = string.Join(", ", grands.Where(g => !noms.TryGetValue(g, out NomCourbe n) || n.Opacite <= 0f).Select(g => guerre.Terres.NomDuPays(g) + (noms.TryGetValue(g, out NomCourbe n) ? " (" + n.CorpsPx.ToString("0.#", CultureInfo.InvariantCulture) + " px)" : " (sans nom)")));
            if (illisibles.Length > 0) throw Faux(cadre + " : noms de pays illisibles : " + illisibles);
            var capitales = villes.Capitales; var sansSiege = new HashSet<string>(villes.Introuvables.Select(i => i.pays));
            string sansMarque = string.Join(", ", grands.Where(g => !sansSiege.Contains(g) && !capitales.Any(c => c.pays.Contains(g) && c.figurine.GetComponent<MeshFilter>().sharedMesh.name.StartsWith("Capitale"))).Select(g => guerre.Terres.NomDuPays(g)));
            if (sansMarque.Length > 0) throw Faux(cadre + " : capitales non marquées : " + sansMarque);
            int capitalesMontrees = capitales.Count(c => c.figurine.gameObject.activeInHierarchy && calques.EtiquetteDe(c.texte)?.enabled == true && cam.pixelRect.Contains((Vector2)cam.WorldToScreenPoint(carte.transform.TransformPoint(c.pied))));
            if (capitalesMontrees == 0) throw Faux(cadre + " : aucune capitale montrée et nommée dans le cadre");
            // Un nom de l'atlas au moins se lit dans le cadre.
            var lisibles = atlas.Noms.Where(n => n.Rendu.enabled && n.Opacite > 0f && cam.pixelRect.Contains((Vector2)cam.WorldToScreenPoint(carte.transform.TransformPoint(carte.SurLeSol(n.Trace.Centre.x, n.Trace.Centre.y, 0f))))).Select(n => n.Texte).ToList();
            if (lisibles.Count == 0) throw Faux(cadre + " : aucun nom de l'atlas ne se lit : " + string.Join(", ", atlas.Noms.Where(n => atlas.SorteDe(n) == AtlasDeCarte.MER).Select(n => n.Texte + " " + n.CorpsPx.ToString("0.#", CultureInfo.InvariantCulture) + " px op " + n.Opacite.ToString("0.##", CultureInfo.InvariantCulture) + (n.Masque ? " masqué" : "") + (n.Rendu.enabled ? "" : " éteint"))));
            // Deux pays voisins dans le cadre n'ont pas la même couleur.
            var presents = new HashSet<string>(guerre.Terres.Terres.Where(t => t.Pays != null && Dans(t.CellId)).Select(t => t.Pays)); int paires = 0;
            foreach (string a in presents) if (guerre.Couleurs.Voisins.TryGetValue(a, out var voisins)) foreach (string b in voisins.Where(presents.Contains))
                    { paires++; if (((Color32)guerre.CouleurDuPays(a)).Equals((Color32)guerre.CouleurDuPays(b))) throw Faux(cadre + " : " + guerre.Terres.NomDuPays(a) + " et " + guerre.Terres.NomDuPays(b) + ", voisins, ont la même couleur"); }
            if (paires == 0) throw Faux(cadre + " : aucun voisinage dans le cadre");
            if (cadre == "maghreb-et-zab")
            {
                var biskra = capitales.SingleOrDefault(c => c.nom == "Biskra");
                if (biskra.texte == null || !biskra.figurine.GetComponent<MeshFilter>().sharedMesh.name.StartsWith("Capitale")) throw Faux("Biskra n'est pas marquée capitale");
                if (calques.EtiquetteDe(biskra.texte)?.enabled != true) throw Faux("Biskra n'est pas nommée sur la carte");
            }
            // Les textes posés en double, s'il y en a, se disent au journal.
            var doubles = carte.GetComponentsInChildren<TextMesh>(false).Where(t => calques.EtiquetteDe(t)?.enabled == true).GroupBy(t => t.text).Where(g => g.Count() > 1).Select(g => g.Key + " ×" + g.Count() + " (" + string.Join(" ; ", g.Select(t => t.transform.parent.name)) + ")");
            Debug.Log("CAPTURE carte-politique " + cadre + " : demi " + demi.ToString("0", CultureInfo.InvariantCulture) + " km ; pays lisibles : "
                + string.Join(", ", grands.Where(noms.ContainsKey).Select(g => guerre.Terres.NomDuPays(g) + " " + noms[g].CorpsPx.ToString("0", CultureInfo.InvariantCulture) + " px")) + " ; capitales montrées " + capitalesMontrees
                + " ; atlas : " + string.Join(", ", lisibles.Take(12)) + " ; " + paires / 2 + " voisinages ; doubles : " + string.Join(", ", doubles));
            yield return cam;
        }

        static InvalidOperationException Faux(string raison) => new InvalidOperationException("carte politique : " + raison);
    }
}
