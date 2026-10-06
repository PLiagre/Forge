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
    // Lot 263 : la recette du chantier sur la cellule du panneau. La caméra ne bouge pas :
    // le second texte est attaché à celle de la scène, et le plan fixe sert de comparaison.
    static class Lot263
    {
        const int IMAGES_DE_POSE = 10;
        const double ATTENTE_S = 20;
        const int DELAI_S = 30;

        [ScenarioDeCapture(263, "chantier")]
        static IEnumerator Chantier(Camera camera)
        {
            if (camera == null)
                throw new InvalidOperationException("la scène n'a pas de caméra");
            var panneau = Object.FindFirstObjectByType<PanneauLieu>();
            if (panneau == null)
                throw new InvalidOperationException("la scène n'a pas de PanneauLieu");
            long cellule = PanneauLieu.LireCellule(Environment.GetCommandLineArgs(), PanneauLieu.CELLULE_PAR_DEFAUT, out _);
            string prefixe = "Cellule " + cellule.ToString(CultureInfo.InvariantCulture) + " · tick ";
            long attendu = TickDe(panneau.TexteAffiche, prefixe) + 4;
            Task.Run(() => Recette(panneau.port, cellule)).GetAwaiter().GetResult();
            string tete = prefixe + attendu.ToString(CultureInfo.InvariantCulture);
            double echeance = Time.realtimeSinceStartupAsDouble + ATTENTE_S;
            while (!AuTick(panneau.TexteAffiche, tete))
            {
                if (Time.realtimeSinceStartupAsDouble > echeance)
                    throw new InvalidOperationException("le panneau n'atteint pas le tick " + attendu + " : " + panneau.TexteAffiche);
                yield return null;
            }
            string foyers = panneau.TexteFoyers ?? "";
            if (!Ligne(foyers, "artisans : ", false) || !Ligne(foyers, "Au chantier : ", true) || !Ligne(foyers, "Logement des artisans : ", true))
                throw new InvalidOperationException("foyers, chantier ou logement illisibles : " + foyers);
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;
        }

        static bool AuTick(string texte, string tete) =>
            texte != null && texte.StartsWith(tete, StringComparison.Ordinal)
            && (texte.Length == tete.Length || texte[tete.Length] == '\n');

        static long TickDe(string texte, string prefixe)
        {
            if (texte == null || !texte.StartsWith(prefixe, StringComparison.Ordinal))
                throw new InvalidOperationException("pas de tick au panneau : " + texte);
            int debut = prefixe.Length, i = debut;
            while (i < texte.Length && texte[i] >= '0' && texte[i] <= '9') i++;
            if (i == debut || i >= texte.Length || texte[i] != '\n')
                throw new InvalidOperationException("tick illisible : " + texte);
            return long.Parse(texte.Substring(debut, i - debut), CultureInfo.InvariantCulture);
        }

        // `nombre` : la ligne commence par `debut` puis un entier (les bras, les logés).
        static bool Ligne(string texte, string debut, bool nombre)
        {
            foreach (string ligne in texte.Split('\n'))
            {
                if (!ligne.StartsWith(debut, StringComparison.Ordinal)) continue;
                if (!nombre) return true;
                int i = debut.Length, chiffres = 0;
                while (i < ligne.Length && ligne[i] >= '0' && ligne[i] <= '9') { chiffres++; i++; }
                return chiffres > 0;
            }
            return false;
        }

        // Hors du fil de l'éditeur : y attendre HttpClient peut ne jamais revenir.
        static void Recette(int port, long cellule)
        {
            string c = cellule.ToString(CultureInfo.InvariantCulture);
            string url = "http://127.0.0.1:" + port.ToString(CultureInfo.InvariantCulture) + "/tick?n=1";
            using (var depot = new ClientIntention(port, TimeSpan.FromSeconds(DELAI_S)))
            using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(DELAI_S) })
            {
                void Geste(string json)
                {
                    RecuIntention recu = depot.Deposer(json);
                    if (!recu.Acceptee)
                        throw new InvalidOperationException("dépôt refusé : " + (recu.Presente ? recu.Erreur : recu.Absence));
                }
                void Tick()
                {
                    using (var corps = new ByteArrayContent(new byte[0]))
                    using (var reponse = http.PostAsync(url, corps).GetAwaiter().GetResult())
                        if ((int)reponse.StatusCode != 200)
                            throw new InvalidOperationException("POST " + url + " a rendu " + (int)reponse.StatusCode);
                }
                Geste("{\"type\":\"tracer_route\",\"cell\":" + c + ",\"points\":[[0,0],[20,0]],\"largeur_m\":1,\"foyers\":100}");
                Tick();
                Geste("{\"type\":\"decouper_parcelle\",\"cell\":" + c + ",\"rue\":0,\"segment\":0,\"debut_m\":0,\"facade_m\":4,\"profondeur_m\":10,\"cote\":\"gauche\",\"foyers\":100}");
                Geste("{\"type\":\"decouper_parcelle\",\"cell\":" + c + ",\"rue\":0,\"segment\":0,\"debut_m\":6,\"facade_m\":8,\"profondeur_m\":20,\"cote\":\"gauche\",\"foyers\":100}");
                Tick();
                Geste("{\"type\":\"poser_batiment\",\"cell\":" + c + ",\"parcelle\":0,\"nature\":\"maison\",\"foyers\":100}");
                Geste("{\"type\":\"poser_batiment\",\"cell\":" + c + ",\"parcelle\":1,\"nature\":\"four\",\"foyers\":100}");
                Tick();
                Tick();
            }
        }
    }
}
