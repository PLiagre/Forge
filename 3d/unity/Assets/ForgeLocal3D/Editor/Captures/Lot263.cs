using System;
using System.Collections;
using System.Globalization;
using System.Net.Http;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 263 : la recette du chantier. La caméra ne bouge pas ; le plan fixe compare.
    static class Lot263
    {
        [ScenarioDeCapture(263, "chantier")]
        static IEnumerator Chantier(Camera camera)
        {
            if (camera == null) throw new InvalidOperationException("la scène n'a pas de caméra");
            var panneau = Object.FindFirstObjectByType<PanneauLieu>() ?? throw new InvalidOperationException("la scène n'a pas de PanneauLieu");
            long cellule = PanneauLieu.LireCellule(Environment.GetCommandLineArgs(), PanneauLieu.CELLULE_PAR_DEFAUT, out _);
            string prefixe = "Cellule " + cellule.ToString(CultureInfo.InvariantCulture) + " · tick ";
            long attendu = TickDe(panneau.TexteAffiche, prefixe) + 4;
            Task.Run(() => Recette(panneau.port, cellule)).GetAwaiter().GetResult();
            string tete = prefixe + attendu.ToString(CultureInfo.InvariantCulture);
            for (double fin = Time.realtimeSinceStartupAsDouble + 20; !AuTick(panneau.TexteAffiche, tete);)
            {
                if (Time.realtimeSinceStartupAsDouble > fin)
                    throw new InvalidOperationException("le panneau n'atteint pas le tick " + attendu + " : " + panneau.TexteAffiche);
                yield return null;
            }
            string foyers = panneau.TexteFoyers ?? "";
            if (!Ligne(foyers, "artisans : ", false) || !Ligne(foyers, "Au chantier : ", true) || !Ligne(foyers, "Logement des artisans : ", true))
                throw new InvalidOperationException("foyers, chantier ou logement illisibles : " + foyers);
            for (int i = 0; i < 10; i++) yield return null;
        }

        static bool AuTick(string texte, string tete) => texte != null && texte.StartsWith(tete, StringComparison.Ordinal) && (texte.Length == tete.Length || texte[tete.Length] == '\n');

        static long TickDe(string texte, string prefixe)
        {
            if (texte == null || !texte.StartsWith(prefixe, StringComparison.Ordinal)) throw new InvalidOperationException("pas de tick au panneau : " + texte);
            int debut = prefixe.Length, i = debut;
            while (i < texte.Length && texte[i] >= '0' && texte[i] <= '9') i++;
            if (i == debut || i >= texte.Length || texte[i] != '\n') throw new InvalidOperationException("tick illisible : " + texte);
            return long.Parse(texte.Substring(debut, i - debut), CultureInfo.InvariantCulture);
        }

        static bool Ligne(string texte, string debut, bool nombre)
        {
            foreach (string ligne in texte.Split('\n'))
            {
                if (!ligne.StartsWith(debut, StringComparison.Ordinal)) continue;
                if (!nombre) return true;
                int i = debut.Length, n = 0;
                while (i < ligne.Length && ligne[i] >= '0' && ligne[i] <= '9') { n++; i++; }
                return n > 0;
            }
            return false;
        }

        static void Recette(int port, long cellule)
        {
            string c = cellule.ToString(CultureInfo.InvariantCulture);
            string url = "http://127.0.0.1:" + port.ToString(CultureInfo.InvariantCulture) + "/tick?n=1";
            using (var depot = new ClientIntention(port, TimeSpan.FromSeconds(30)))
            using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(30) })
            {
                void Geste(string type, string reste)
                {
                    RecuIntention recu = depot.Deposer("{\"type\":\"" + type + "\",\"cell\":" + c + "," + reste + ",\"foyers\":100}");
                    if (!recu.Acceptee) throw new InvalidOperationException("dépôt refusé : " + (recu.Presente ? recu.Erreur : recu.Absence));
                }
                void Tick()
                {
                    using (var reponse = http.PostAsync(url, new ByteArrayContent(new byte[0])).GetAwaiter().GetResult())
                        if ((int)reponse.StatusCode != 200) throw new InvalidOperationException("POST " + url + " a rendu " + (int)reponse.StatusCode);
                }
                Geste("tracer_route", "\"points\":[[0,0],[20,0]],\"largeur_m\":1"); Tick();
                Geste("decouper_parcelle", "\"rue\":0,\"segment\":0,\"debut_m\":0,\"facade_m\":4,\"profondeur_m\":10,\"cote\":\"gauche\"");
                Geste("decouper_parcelle", "\"rue\":0,\"segment\":0,\"debut_m\":6,\"facade_m\":8,\"profondeur_m\":20,\"cote\":\"gauche\""); Tick();
                Geste("poser_batiment", "\"parcelle\":0,\"nature\":\"maison\"");
                Geste("poser_batiment", "\"parcelle\":1,\"nature\":\"four\""); Tick(); Tick();
            }
        }
    }
}
