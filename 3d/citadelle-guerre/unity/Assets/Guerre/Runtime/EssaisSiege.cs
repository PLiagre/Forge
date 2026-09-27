using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Unity.Collections;
using Unity.Entities;
using Unity.Mathematics;
using Unity.Transforms;
using UnityEngine;

namespace Guerre
{
    // Essai du jalon 9 dans le vrai joueur :
    //   Citadelle-Guerre.exe -guerre-essai-siege -guerre-soldats 2000 -guerre-sortie DOSSIER [-guerre-sans-chocs]
    // La porte de la citadelle est fermée : aucune route ne mène plus du pied de l'éperon à la place de la
    // cathédrale. Quatre bombardes, au bord du ravin, et deux trébuchets tirent sur le pied d'un pan de mur
    // appareillé. Dès qu'une route existe, la batterie cesse le feu et un régiment de 250 piquiers reçoit
    // l'ordre d'aller sur la place. La brèche ouverte par l'artillerie est franchissable si la route passe par
    // elle, si 95 % des hommes arrivent à leur place, et si aucun ne passe dans une pierre encore en place
    // ni dans l'emprise d'un mur ou d'une maison.
    // Avec -guerre-sans-chocs, les boulets frappent sans rien déloger : aucune brèche, l'essai doit échouer.
    public sealed class EssaisSiege : MonoBehaviour
    {
        [Serializable] public class Rapport
        {
            public string statut, date_utc; public bool sans_chocs;
            public bool fermee_avant, breche_ouverte, route_par_la_breche, arrive;
            public float breche_apres_s, marche_s, a_sa_place, distance_route_breche_m;
            public int tirs, pierres, pierres_delogees_ou_tombees, pierres_a_terre, pierres_au_mur, files_en_colonne, dans_un_mur_max;
            public float longueur_route_m;
            public string[] motifs;
            public string[] dans_un_mur_cas;   // où, quand et dans quoi : pour comprendre un échec
            public int bouchon_max; public float bouchon_t, bouchon_s;   // hommes arrêtés près de la brèche, au plus ; quand ; combien de temps plus de 30
        }

        static string sortie; static bool sansChocs;
        const float LimiteFeu = 5400f, LimiteMarche = 1500f, Reste = 30f, APlace = 2.5f, PartMin = 0.95f, PresDeLaBreche = 12f;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Demarrer()
        {
            var args = Environment.GetCommandLineArgs();
            if (!args.Contains("-guerre-essai-siege")) return;
            int i = Array.IndexOf(args, "-guerre-sortie");
            sortie = i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.Combine(Application.persistentDataPath, "essai-siege");
            sansChocs = args.Contains("-guerre-sans-chocs");
            var go = new GameObject("Essais de siège"); DontDestroyOnLoad(go); go.AddComponent<EssaisSiege>();
        }

        IEnumerator Start()
        {
            Directory.CreateDirectory(sortie);
            // L'essai ne mesure pas le temps d'image : il garde le plafond du jeu, 60 images/s. La simulation avance
            // à pas fixe, plusieurs pas par image en accéléré : ses issues n'en dépendent pas.
            QualitySettings.vSyncCount = 0; Application.targetFrameRate = 60;
            while (Bataille.Instance == null || !Bataille.Instance.Pret) yield return null;
            var b = Bataille.Instance; var em = b.Em; var carte = b.carte;
            var murs = World.DefaultGameObjectInjectionWorld.GetExistingSystemManaged<SystemeMurs>();
            var cmd = FindFirstObjectByType<Commandement>(); cmd.automatique = true; cmd.montrerAide = false;
            b.Ordonner(b.Regiments().Select(x => (x.e, x.r.Position, x.r.Front, x.r.Files)).ToList());
            yield return null;
            var r = new Rapport { date_utc = DateTime.UtcNow.ToString("o"), sans_chocs = sansChocs };
            var motifs = new List<string>();
            if (carte == null || carte.pans.Count == 0 || !murs.Pret) { motifs.Add("la carte n'a pas de pan de mur appareillé"); Finir(r, motifs); yield break; }
            r.pierres = murs.Etats.Length;

            var pied = carte.Trouver("pied"); var place = carte.Trouver("place"); var breche = carte.Trouver("breche");
            // Les régiments qui ne marchent pas sont rangés au sud de la vallée.
            var tous = b.Regiments(0).OrderBy(x => x.r.Index).Select(x => x.e).ToList();
            var marcheur = tous[0];
            var autres = b.Regiments().Select(x => x.e).Where(e => e != marcheur).ToArray();
            for (int k = 0; k < autres.Length; k++)
            {
                float x = 330f + k * 1700f / Math.Max(1, autres.Length - 1);
                b.Deplacer(autres[k], new float2(x, 1200f + 90f * math.sin(x / 520f) - 250f), new float2(1, 0), 25);
            }
            // Le régiment d'assaut attend la brèche au débouché du pont, de l'autre côté du ravin, à 12 m du tablier.
            var pont = carte.tabliers.First(x => x.nom == "pont");
            float2 axePont = new float2(-math.sin(pont.angle), math.cos(pont.angle));
            float2 bout = (float2)pont.centre + axePont * pont.demi.y, autreBout = (float2)pont.centre - axePont * pont.demi.y;
            float2 centreVille = carte.Trouver("citadelle").p;
            if (math.distance(autreBout, centreVille) > math.distance(bout, centreVille)) bout = autreBout;
            float2 dehorsPont = math.normalize(bout - (float2)pont.centre), attente = bout + dehorsPont * 12f;
            b.Armer(marcheur, 0);
            b.Deplacer(marcheur, attente, -dehorsPont, 25);

            // La porte fermée, il n'y a plus de route : ni du pied de l'éperon, ni du pont.
            b.FermerPorte();
            const float MargeColonne = 0.4f + 0.5f + 1.1f;   // un corps, la demi-case, une file de chaque côté : trois files
            r.fermee_avant = b.Planificateur.Chercher(pied.p, place.p, MargeColonne, out _) == null
                          && b.Planificateur.Chercher(attente, place.p, MargeColonne, out _) == null;
            if (!r.fermee_avant) motifs.Add("la porte fermée, une route mène encore à la place : l'essai ne prouve rien");
            Diagnostic(b, murs, carte, Path.Combine(sortie, "diagnostic_avant.txt"));
            Grille(b, breche.p, MargeColonne, Path.Combine(sortie, "grille_avant.png"));

            // La batterie.
            var engins = new List<Engin>();
            foreach (var poste in carte.batterie)
            {
                var modele = poste.trebuchet ? b.trebuchet : b.bombarde;
                var vers = poste.cible - poste.place; vers.y = 0;
                var go = Instantiate(modele, poste.place, Quaternion.LookRotation(vers.normalized, Vector3.up));
                var en = go.AddComponent<Engin>();
                en.trebuchet = poste.trebuchet; en.cible = poste.cible; en.etendue = poste.etendue;
                if (poste.trebuchet) { en.cadence = 60f; en.vitesse = 55f; en.masse = 120f; en.rayon = 0.3f; en.dispersion = 0.6f; }
                else { en.cadence = 90f; en.vitesse = 110f; en.masse = 150f; en.rayon = 0.25f; en.dispersion = 0.3f; en.hauteurBouche = 0.85f; }
                engins.Add(en);
            }
            yield return null;
            foreach (var en in engins) en.actif = true;
            var vueBreche = new Vector3(breche.p.x, 0, breche.p.y);
            cmd.foyer = vueBreche - new Vector3(breche.front.x, 0, breche.front.y) * 10f; cmd.plongee = 18; cmd.distance = 60;
            cmd.cap = Mathf.Atan2(breche.front.x, breche.front.y) * Mathf.Rad2Deg;
            Time.timeScale = 16;

            // Le feu, jusqu'à ce qu'une route existe (on la cherche toutes les 30 s).
            float debut = Time.time, prochaine = 0; bool premiere = false;
            while (Time.time - debut < LimiteFeu)
            {
                yield return null;
                if (!premiere && murs.AuMur < r.pierres - 40) { premiere = true; yield return Capture("premieres_pierres"); }
                if (Time.time < prochaine) continue;
                prochaine = Time.time + 30f;
                if (b.Planificateur.Chercher(attente, place.p, MargeColonne, out _) != null) { r.breche_ouverte = true; r.breche_apres_s = Time.time - debut; break; }
            }
            foreach (var en in engins) en.actif = false;
            r.tirs = engins.Sum(x => x.tires);
            // On laisse retomber ce qui tombe encore.
            float repos = Time.time; while (Time.time - repos < 20f) yield return null;
            cmd.plongee = 30; cmd.distance = 70;
            yield return Capture("breche");
            em.CompleteAllTrackedJobs();
            Grille(b, breche.p, MargeColonne, Path.Combine(sortie, "grille_breche.png"));
            Diagnostic(b, murs, carte, Path.Combine(sortie, "diagnostic.txt"));
            if (!r.breche_ouverte)
            {
                // Pas de brèche : il n'y a pas d'assaut à donner.
                murs.Compter(out r.pierres_au_mur, out r.pierres_a_terre);
                r.pierres_delogees_ou_tombees = r.pierres - r.pierres_au_mur;
                motifs.Add($"aucune brèche franchissable après {LimiteFeu:0} s de feu ({r.tirs} tirs, {r.pierres_delogees_ou_tombees} pierres délogées ou tombées)");
                Time.timeScale = 1;
                Finir(r, motifs);
                yield break;
            }

            // L'assaut : l'ordre d'aller sur la place, comme le joueur le donnerait.
            b.Ordonner(marcheur, place.p, place.front, 25);
            var reg = em.GetComponentData<Regiment>(marcheur);
            r.files_en_colonne = reg.Chemin != 0 ? reg.Files : 0;
            r.longueur_route_m = reg.Chemin != 0 ? reg.LongueurChemin : 0;
            var route = em.GetBuffer<PointChemin>(marcheur);
            r.distance_route_breche_m = float.MaxValue;
            // La route passe-t-elle par la brèche ? On regarde les segments, pas seulement les sommets.
            for (int k = 1; k < route.Length; k++)
            {
                float2 a = route[k - 1].P, d = route[k].P - a;
                float u = math.saturate(math.dot((float2)breche.p - a, d) / math.max(math.lengthsq(d), 1e-6f));
                r.distance_route_breche_m = math.min(r.distance_route_breche_m, math.distance(a + d * u, (float2)breche.p));
            }
            r.route_par_la_breche = reg.Chemin != 0 && r.distance_route_breche_m < PresDeLaBreche;
            Time.timeScale = 4;

            // La vraie géométrie : les emprises de la carte et la porte fermée ; les pierres en place, à leur hauteur.
            var t0 = b.terrain.transform.position; int cote = Mathf.CeilToInt(b.terrain.terrainData.size.x);
            float2 origine = new float2(t0.x, t0.z);
            var emprises = new byte[cote * cote];
            foreach (var bl in carte.blocs) Bataille.Tracer(emprises, cote, origine, bl);
            Bataille.Tracer(emprises, cote, origine, new CarteDonnees.Bloc { centre = carte.porte.centre, demi = carte.porte.demi, angle = carte.porte.angle });
            var soldats = em.CreateEntityQuery(typeof(Soldat), typeof(LocalTransform));
            float depart = Time.time, arrivee = -1; prochaine = 0; bool dansLaBreche = false;
            var cas = new List<string>();   // les hommes trouvés dans une pierre ou une emprise, pour le diagnostic
            var releves = new List<Dictionary<int, float2>>(); float prochainReleve = 0; bool bouchonVu = false;
            float2 axeBreche = new float2(-breche.front.y, breche.front.x);
            while (Time.time - depart < LimiteMarche)
            {
                yield return null;
                if (Time.time < prochaine) continue;
                prochaine = Time.time + 0.5f;
                em.CompleteAllTrackedJobs();
                int dedans = 0, pres = 0;
                using (var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp))
                using (var tt = soldats.ToComponentDataArray<LocalTransform>(Allocator.Temp))
                    for (int i = 0; i < ss.Length; i++)
                    {
                        if (ss[i].Regiment != marcheur) continue;
                        float3 p = tt[i].Position;
                        int2 c = (int2)math.floor(p.xz - origine);
                        float2 dp = p.xz - (float2)breche.p;
                        string Ou() => $"t {Time.time - depart:0} s, homme {ss[i].Numero} à (x {math.dot(dp, axeBreche):0.00} ; s {math.dot(dp, (float2)breche.front):0.00}), pieds {p.y:0.00}, case {b.Couches(p.xz)}";
                        if (c.x >= 0 && c.y >= 0 && c.x < cote && c.y < cote && emprises[c.y * cote + c.x] != 0)
                        {
                            dedans++;
                            if (cas.Count < 12) cas.Add(Ou() + " : dans une emprise");
                            continue;
                        }
                        if (math.distance(p.xz, breche.p) > 20f) continue;
                        pres++;
                        for (int j = 0; j < murs.Etats.Length; j++)
                        {
                            if (murs.Etats[j] != 0) continue;
                            float3 cp = murs.Centres[j], tp = murs.Tailles[j];
                            if (cp.y - tp.y / 2 > p.y + 1.7f || cp.y + tp.y / 2 < p.y + 0.3f) continue;
                            float3 l = math.mul(math.inverse(murs.Orientations[j]), p - cp);
                            if (math.abs(l.x) < tp.x / 2 && math.abs(l.z) < tp.z / 2)
                            {
                                dedans++;
                                float solPierre = b.SolEn(cp.xz);
                                if (cas.Count < 12) cas.Add(Ou() + $" : dans la pierre {j} (pan {murs.Pans[j]}, épaisseur {murs.Couches[j]}, assise {murs.Assises[j]}, {tp.x:0.00} × {tp.z:0.00} m, "
                                    + $"bas {cp.y - tp.y / 2 - solPierre:0.00} et haut {cp.y + tp.y / 2 - solPierre:0.00} au-dessus du sol sous son centre ({solPierre:0.00}), local ({l.x:0.00} ; {l.z:0.00}), case du centre {b.Couches(cp.xz)})");
                                break;
                            }
                        }
                    }
                r.dans_un_mur_max = Math.Max(r.dans_un_mur_max, dedans);

                // Les bouchons : toutes les 5 s, les hommes à moins de 15 m de la brèche qui n'ont pas fait un mètre
                // en 10 s, tant que la colonne est en route.
                if (Time.time - depart >= prochainReleve)
                {
                    prochainReleve += 5f;
                    var ici = new Dictionary<int, float2>();
                    var arretes = new List<(float2, Color)>();
                    using (var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp))
                    using (var tt = soldats.ToComponentDataArray<LocalTransform>(Allocator.Temp))
                        for (int i = 0; i < ss.Length; i++)
                        {
                            if (ss[i].Regiment != marcheur) continue;
                            float2 p = tt[i].Position.xz;
                            ici[ss[i].Numero] = p;
                            bool arrete = releves.Count >= 2 && releves[releves.Count - 2].TryGetValue(ss[i].Numero, out var avant)
                                          && math.distance(avant, p) < 1f && math.distance(p, breche.p) < 15f;
                            arretes.Add((p, arrete ? Color.red : new Color(0.25f, 0.2f, 0.2f)));
                        }
                    releves.Add(ici);
                    int n = arretes.Count(x => x.Item2 == Color.red);
                    if (em.GetComponentData<Regiment>(marcheur).Chemin != 0)
                    {
                        if (n > 30) r.bouchon_s += 5f;
                        if (n > r.bouchon_max) { r.bouchon_max = n; r.bouchon_t = Time.time - depart; }
                        if (n >= 40 && !bouchonVu)
                        {
                            bouchonVu = true;
                            var rt = em.GetBuffer<PointChemin>(marcheur);
                            for (int k = 0; k < rt.Length; k++) arretes.Insert(0, (rt[k].P, Color.yellow));
                            Grille(b, breche.p, MargeColonne, Path.Combine(sortie, "grille_bouchon.png"), arretes);
                            cmd.foyer = vueBreche; cmd.plongee = 50; cmd.distance = 40;
                            yield return Capture("bouchon");
                        }
                    }
                }
                if (!dansLaBreche && pres > 20)
                {
                    dansLaBreche = true;
                    cmd.foyer = vueBreche; cmd.plongee = 35; cmd.distance = 45;
                    yield return Capture("assaut_par_la_breche");
                }
                var rg = em.GetComponentData<Regiment>(marcheur);
                if (arrivee < 0 && rg.Chemin == 0 && math.distance(rg.Position, place.p) < 1f) arrivee = Time.time;
                if (arrivee >= 0 && Time.time - arrivee > Reste) break;
            }
            Time.timeScale = 1;
            r.dans_un_mur_cas = cas.ToArray();
            em.CompleteAllTrackedJobs();
            using (var ss = soldats.ToComponentDataArray<Soldat>(Allocator.Temp))
            using (var tt = soldats.ToComponentDataArray<LocalTransform>(Allocator.Temp))
            {
                var rg = em.GetComponentData<Regiment>(marcheur);
                int n = 0, bien = 0;
                for (int i = 0; i < ss.Length; i++)
                {
                    if (ss[i].Regiment != marcheur) continue;
                    n++;
                    float2 pl = Formation.VersMonde(Formation.Place(rg, ss[i].Numero) + ss[i].Decalage, rg.Position, rg.Front);
                    if (math.distance(pl, tt[i].Position.xz) < APlace) bien++;
                }
                r.a_sa_place = n > 0 ? bien / (float)n : 0;
            }
            r.arrive = arrivee >= 0;
            r.marche_s = (arrivee >= 0 ? arrivee : Time.time) - depart;
            murs.Compter(out r.pierres_au_mur, out r.pierres_a_terre);
            r.pierres_delogees_ou_tombees = r.pierres - r.pierres_au_mur;
            cmd.foyer = new Vector3(place.p.x, 0, place.p.y); cmd.plongee = 60; cmd.distance = 80; cmd.cap = 0;
            yield return Capture("arrivee_sur_la_place");

            if (!r.route_par_la_breche) motifs.Add($"la route ne passe pas par la brèche (à {r.distance_route_breche_m:0} m)");
            if (!r.arrive) motifs.Add($"le régiment n'est pas arrivé sur la place en {LimiteMarche:0} s");
            if (r.a_sa_place < PartMin) motifs.Add($"{r.a_sa_place:P0} des hommes à leur place à l'arrivée (au moins {PartMin:P0})");
            if (r.dans_un_mur_max > 0) motifs.Add($"jusqu'à {r.dans_un_mur_max} hommes dans une pierre en place ou l'emprise d'un mur");
            Finir(r, motifs);
        }

        // Diagnostic : la grille des obstacles autour de la brèche, quatre pixels par mètre. Noir : une emprise ;
        // brun : une pente trop raide ; bleu : une pierre en place ; vert : assez de dégagement pour trois files.
        // Des points peuvent s'y ajouter (des hommes, une route), deux pixels de côté.
        static void Grille(Bataille b, float2 centre, float marge, string chemin, List<(float2 p, Color c)> points = null)
        {
            const int N = 320;
            var img = new Texture2D(N, N, TextureFormat.RGB24, false);
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    var p = centre + new float2(x - N / 2 + 0.5f, y - N / 2 + 0.5f) * 0.25f;
                    int k = b.Couches(p);
                    var couleur = (k & 2) != 0 ? Color.black : (k & 4) != 0 ? new Color(0.15f, 0.3f, 0.85f) : (k & 1) != 0 ? new Color(0.55f, 0.3f, 0.15f)
                        : b.Planificateur.DegagementEn(p) >= marge ? new Color(0.7f, 0.88f, 0.65f) : new Color(0.9f, 0.88f, 0.8f);
                    img.SetPixel(x, y, couleur);
                }
            if (points != null)
                foreach (var (p, c) in points)
                {
                    int2 q = (int2)math.floor((p - centre) / 0.25f) + N / 2;
                    for (int dy = 0; dy < 2; dy++) for (int dx = 0; dx < 2; dx++)
                        if (q.x + dx >= 0 && q.y + dy >= 0 && q.x + dx < N && q.y + dy < N) img.SetPixel(q.x + dx, q.y + dy, c);
                }
            File.WriteAllBytes(chemin, img.EncodeToPNG());
            Destroy(img);
        }

        // Diagnostic : pourquoi une route passe ou non. Profils à travers la brèche, le long du mur et de la lice ;
        // les pierres qui barrent encore ; les routes partielles.
        static void Diagnostic(Bataille b, SystemeMurs murs, CarteDonnees carte, string chemin)
        {
            var sb = new System.Text.StringBuilder();
            var pl = b.Planificateur;
            var breche = carte.Trouver("breche"); var pied = carte.Trouver("pied"); var place = carte.Trouver("place");
            float2 c = breche.p, dedans = breche.front, axe = new float2(-dedans.y, dedans.x);
            string Case(float2 p)
            {
                int k = b.Couches(p);
                return $"sol {b.SolEn(p),7:0.00} grav {b.GravatsEn(p),5:0.00} {((k & 1) != 0 ? "P" : ".")}{((k & 2) != 0 ? "E" : ".")}{((k & 4) != 0 ? "M" : ".")} dég {pl.DegagementEn(p),4:0.0}";
            }
            sb.AppendLine("# À travers la brèche (s < 0 : dehors), sur l'axe de la brèche et à 3 m de part et d'autre");
            for (float s = -16; s <= 16.01f; s += 0.5f)
                sb.AppendLine($"s {s,6:0.0} | {Case(c + dedans * s)} | -3 : {Case(c + dedans * s - axe * 3)} | +3 : {Case(c + dedans * s + axe * 3)}");
            sb.AppendLine("# Le long du mur (x le long du pan du milieu) : sur sa ligne, à 2,5 m dehors et à 2,5 m dedans");
            for (float x = -18; x <= 18.01f; x += 0.5f)
                sb.AppendLine($"x {x,6:0.0} | {Case(c + axe * x)} | dehors : {Case(c + axe * x - dedans * 2.5f)} | dedans : {Case(c + axe * x + dedans * 2.5f)}");

            // La lice : de la brèche à la porte, en arc autour du centre de la ville. À chaque pas, la coupe
            // en travers (du pied du mur au bord du ravin) et le plus grand dégagement qu'on y trouve.
            float2 centre = carte.Trouver("citadelle").p;
            float2 vb = c - centre, vp = (float2)carte.porte.centre - centre;
            float r0 = math.length(vb), a0 = math.atan2(vb.y, vb.x), a1 = math.atan2(vp.y, vp.x);
            if (a1 < a0) a1 += 2 * math.PI;
            sb.AppendLine($"# La lice, de la brèche (angle {math.degrees(a0):0.0}°) à la porte ({math.degrees(a1):0.0}°) ; coupe de r = {r0 - 2:0} à {r0 + 18:0} m, un signe par 0,5 m");
            for (float a = a0 - math.radians(3); a <= a1 + 0.0001f; a += 1f / r0)
            {
                var coupe = new System.Text.StringBuilder(); float meilleur = 0, rMeilleur = 0;
                for (float r = r0 - 2; r <= r0 + 18; r += 0.5f)
                {
                    float2 p = centre + r * new float2(math.cos(a), math.sin(a));
                    int k = b.Couches(p); float d = pl.DegagementEn(p);
                    coupe.Append((k & 2) != 0 ? '#' : (k & 4) != 0 ? 'M' : (k & 1) != 0 ? 'P' : d >= 2f ? '+' : '.');
                    if (d > meilleur) { meilleur = d; rMeilleur = r; }
                }
                sb.AppendLine($"{math.degrees(a),6:0.0}° {coupe} dég max {meilleur:0.0} à r {rMeilleur:0.0}");
            }

            // Les routes partielles, à trois marges : trois files, deux, une.
            float2 dehors = c - dedans * 6f, interieur = c + dedans * 6f;
            foreach (var (nom, a, z) in new[] { ("pied → lice devant la brèche", (float2)pied.p, dehors), ("lice → derrière la brèche", dehors, interieur),
                                                ("derrière la brèche → place", interieur, (float2)place.p), ("pied → place", (float2)pied.p, (float2)place.p) })
                foreach (float marge in new[] { 2.0f, 1.45f, 0.9f })
                {
                    var route = pl.Chercher(a, z, marge, out float etroit);
                    sb.AppendLine($"route {nom}, marge {marge:0.00} : " + (route == null ? "aucune" : $"{route.Count} cases, le plus étroit {etroit:0.0} m"));
                    // Là où la route traverse le mur : ses points dans le repère de la brèche (x le long du mur, s vers l'intérieur).
                    if (route != null && nom.StartsWith("lice"))
                        sb.AppendLine("   (x ; s) " + string.Join(" ", route.Select(q => { float2 d = (float2)q - c; return $"({math.dot(d, axe):0.0} ; {math.dot(d, dedans):0.0})"; })));
                }

            // Les pierres : ce qui reste debout de chaque assise du pan du milieu, et les pierres qui barrent encore.
            int nb = murs.Etats.Length;
            sb.AppendLine("# Pan du milieu : par assise, les pierres en place (ext/blocage/int) et les vides où les trois épaisseurs sont tombées");
            var pan = carte.pans[1];
            float phi = math.radians(pan.exterieur);
            float3 axePan = math.mul(quaternion.LookRotationSafe(new float3(math.cos(phi), 0, math.sin(phi)), math.up()), new float3(1, 0, 0));
            int maxAssise = 0; for (int i = 0; i < nb; i++) if (murs.Pans[i] == 1) maxAssise = Math.Max(maxAssise, murs.Assises[i]);
            for (int a = maxAssise; a >= 0; a--)
            {
                var n3 = new int[3]; var pleins = new List<float2>();
                for (int i = 0; i < nb; i++)
                {
                    if (murs.Pans[i] != 1 || murs.Assises[i] != a || murs.Etats[i] != 0) continue;
                    n3[murs.Couches[i]]++;
                    float x = math.dot(murs.Centres[i] - (float3)pan.pied, axePan);
                    pleins.Add(new float2(x - murs.Tailles[i].x / 2, x + murs.Tailles[i].x / 2));
                }
                pleins.Sort((u, v) => u.x.CompareTo(v.x));
                var vides = new List<string>(); float fin = -pan.longueur / 2;
                foreach (var q in pleins) { if (q.x - fin > 0.3f) vides.Add($"[{fin:0.0} ; {q.x:0.0}]"); fin = math.max(fin, q.y); }
                if (pan.longueur / 2 - fin > 0.3f) vides.Add($"[{fin:0.0} ; {pan.longueur / 2:0.0}]");
                sb.AppendLine($"assise {a,2} : {n3[0],2}/{n3[1],2}/{n3[2],2}  vides {string.Join(" ", vides)}");
            }
            sb.AppendLine($"# Pierres en place qui barrent un passage (tranche [sol + 0,3 ; sol + {Bataille.Passage:0.0}]) à moins de 10 m de la brèche");
            sb.AppendLine("pan couche assise  x_axe   bas/sol  haut/sol  sol     gravats");
            int barrent = 0;
            for (int i = 0; i < nb; i++)
            {
                if (murs.Etats[i] != 0) continue;
                float3 cp = murs.Centres[i], tp = murs.Tailles[i];
                if (math.distance(cp.xz, c) > 10f) continue;
                float sol = b.SolEn(cp.xz), bas = cp.y - tp.y / 2 - sol, haut = cp.y + tp.y / 2 - sol;
                if (bas > Bataille.Passage || haut < 0.3f) continue;
                barrent++;
                sb.AppendLine($"{murs.Pans[i],3} {murs.Couches[i],6} {murs.Assises[i],6} {math.dot(cp.xz - c, axe),7:0.00} {bas,8:0.00} {haut,8:0.00} {sol,8:0.00} {b.GravatsEn(cp.xz),6:0.00}");
            }
            sb.AppendLine($"{barrent} pierres barrent encore");
            File.WriteAllText(chemin, sb.ToString());
        }

        void Finir(Rapport r, List<string> motifs)
        {
            r.motifs = motifs.ToArray();
            r.statut = motifs.Count == 0 ? "valide" : "echec";
            File.WriteAllText(Path.Combine(sortie, "essai-siege.json"), JsonUtility.ToJson(r, true));
            Debug.Log("[EssaisSiege] " + r.statut + " " + string.Join(" | ", motifs));
            Application.Quit(motifs.Count == 0 ? 0 : 1);
        }

        IEnumerator Capture(string nom)
        {
            float ts = Time.timeScale; Time.timeScale = 0;
            for (int k = 0; k < 6; k++) yield return null;
            yield return new WaitForEndOfFrame();
            var img = ScreenCapture.CaptureScreenshotAsTexture();
            File.WriteAllBytes(Path.Combine(sortie, nom + ".jpg"), img.EncodeToJPG(85));
            Destroy(img);
            Time.timeScale = ts;
        }
    }
}
