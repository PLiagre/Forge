using System;
using System.Collections;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using Object = UnityEngine.Object;
namespace ForgeLocal3D.Captures
{
    static class Lot697
    {
        [ScenarioDeCapture(697, "biskra-en-montagne")]
        static IEnumerator BiskraEnMontagne(Camera camera)
        {
            var outil = Object.FindFirstObjectByType<DesertRoadTool>() ?? throw new InvalidOperationException("pas d'outil des routes");
            var ville = Object.FindFirstObjectByType<DesertCityCamera>() ?? throw new InvalidOperationException("pas de caméra de ville");
            var lieu = Object.FindFirstObjectByType<PanneauLieu>() ?? throw new InvalidOperationException("pas de panneau du lieu");
            if (ville.GetComponent<Camera>() != camera) throw new InvalidOperationException("la caméra de la photo n'est pas celle de la ville");
            outil.automatique = true; ville.automatique = true;
            var lecture = Task.Run(() => { using (var d = new ClientDeparts(outil.Port, ClientDeparts.DelaiMinimal)) return d.Lire(); });
            for (double fin = Time.realtimeSinceStartupAsDouble + 30; !lecture.IsCompleted;) { if (Time.realtimeSinceStartupAsDouble > fin) throw new InvalidOperationException("pas de /departs"); yield return null; }
            if (lecture.IsFaulted || !lecture.Result.Presente) throw new InvalidOperationException(lecture.Exception?.GetBaseException().Message ?? lecture.Result.Absence);
            var fiches = lecture.Result.Donnees.Fiches.Where(f => f.Siege.Nom == "Biskra").ToArray();
            if (fiches.Length != 1) throw new InvalidOperationException(fiches.Length + " siège(s) Biskra");
            if (!outil.Ouvrir(fiches[0].CellId)) throw new InvalidOperationException("ouverture refusée : " + outil.Message);
            lieu.Ouvrir(fiches[0].CellId);
            var mesh = GameObject.Find("Panneau des routes")?.GetComponent<TextMesh>();
            if (mesh == null || !mesh.text.Contains("Relief : montagne") || !Releve(outil))
                throw new InvalidOperationException("panneau ou relèvement : " + (mesh == null ? "absent" : mesh.text));
            ville.VueEnsemble();
            for (int i = 0; i < 8; i++) yield return null;
            outil.Placer();
            if (!mesh.text.Contains("Relief : montagne")) throw new InvalidOperationException("la ligne de relief a disparu");
        }

        static bool Releve(DesertRoadTool outil)
        {
            var roads = outil.roads; var td = roads.Copie; var src = roads.Original;
            if (td == null || src == null || !(roads.FacteurRelief > 1)) return false;
            var P = DesertRoads.Lire(roads.implantation).parametres;
            int n = td.heightmapResolution; double pas = td.size.x / (n - 1), moitie = td.size.x / 2, bas = roads.terrain.transform.position.y, tol = 2 * td.size.y / 32766.0;
            for (int k = 1; k <= 8; k++)
            {
                int i = (n - 1) / 2 - k * 80; if (i < 1) continue;
                double x = moitie - i * pas, d = Math.Abs(x); if (d <= 0 || d >= P.relief_plein) continue;
                if (outil.Ouverture.Any(e => e.resultat.acceptee && e.resultat.ax != null && Enumerable.Range(0, e.resultat.ax.Length).Any(t => Math.Abs(e.resultat.ax[t] - x) < 15 && Math.Abs(e.resultat.ay[t] - x) < 15))) continue;
                float a = src.GetHeights(i, i, 1, 1)[0, 0], b = td.GetHeights(i, i, 1, 1)[0, 0];
                double m = bas + a * td.size.y; if (Math.Abs(m - P.pivot) <= 1) continue;
                double f = 1 + (roads.FacteurRelief - 1) * Math.Clamp((P.relief_nul - d) / (P.relief_nul - P.relief_plein), 0, 1);
                if (f > 1 && Math.Abs(bas + b * td.size.y - (P.pivot + (m - P.pivot) * f)) <= tol) return true;
            }
            return false;
        }
    }
}
