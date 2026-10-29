using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Lot 889 : Mistra en noms, en date et en tonnes. `-forge889Territoire` réécrit « Territoire … · lieu 0 » et rougit sur « mot interdit ».
    static class Lot889
    {
        const string DRAPEAU = "-forge889Territoire";
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string Premiere(string t) { string p = (t ?? "").Replace("\r", ""); int i = p.IndexOf('\n'); return i < 0 ? p : p.Substring(0, i); }
        [ScenarioDeCapture(889, "mistra-en-noms")]
        static IEnumerator MistraEnNoms(Camera camera)
        {
            for (var e = Lot655.MistraTerresEtComptes(camera); e.MoveNext();) yield return null;
            DossierMaison dossier = Lot655.Dossier ?? throw Echec("le lot 655 n'a pas gardé le feuillet");
            Text texte = Lot655.Texte ?? throw Echec("le lot 655 n'a pas gardé le texte du feuillet");
            ComptesDeMaison comptes = Lot655.ComptesLus ?? throw Echec("le lot 655 n'a pas gardé les comptes");
            int port = Lot655.Port; if (port < 1) throw Echec("le lot 655 n'a pas gardé le port");
            var tenues = comptes.Maison.Lieux; if (tenues.Count == 0) throw Echec("aucune terre tenue");
            var attendues = new List<string>(); var cellules = new List<string>();
            foreach (LieuTenu tenue in tenues)
            {
                string id = tenue.CellId.ToString(CultureInfo.InvariantCulture); if (!cellules.Contains(id)) cellules.Add(id);
                var lecture = Task.Run(() => { using (var c = new ClientLieu(port, ClientDeparts.DelaiMinimal)) return c.Lire(tenue.CellId); });
                for (var a = Lot690.Attendre(lecture, "lecture /lieu?cell=" + id); a.MoveNext();) yield return null;
                if (!lecture.Result.Presente) throw Echec("/lieu?cell=" + id + " absent : " + lecture.Result.Absence);
                string bourg = Nom(lecture.Result.Lieu, 0);
                attendues.Add(tenue.Rang == 0 ? bourg : bourg + " · " + Nom(lecture.Result.Lieu, tenue.Rang));
            }
            for (var e = Lot690.Jusqua(() => Lignes(dossier.TexteAffiche, attendues), () => "terres « " + string.Join(" | ", attendues) + " » absentes : « " + (dossier.TexteAffiche ?? "(aucun)").Replace("\r", "").Replace("\n", " | ") + " »"); e.MoveNext();) yield return null;
            if (Environment.GetCommandLineArgs().Contains(DRAPEAU)) texte.text += "\nTerritoire " + cellules[0] + " · lieu 0";
            if (texte.text == null || dossier.TexteAffiche == null || !texte.text.StartsWith(dossier.TexteAffiche, StringComparison.Ordinal))
                throw Echec("le texte affiché ne commence pas par le feuillet : « " + Premiere(texte.text) + " »");
            string mot = TexteDuMonde.Interdit(texte.text, cellules.ToArray());
            if (mot != null) throw Echec("mot interdit « " + mot + " » dans le feuillet : « " + Premiere(texte.text) + " »");
            if (TexteDuMonde.SansUnite(texte.text) is string nu) throw Echec("nombre sans unité « " + nu + " » dans le feuillet : « " + Premiere(texte.text) + " »");
            Debug.Log("CAPTURE_889 maison " + comptes.Maison.Id + " ; terres « " + string.Join(" | ", attendues) + " » ; " + Premiere(dossier.TexteAffiche));
        }
        static bool Lignes(string texte, List<string> attendues) => texte != null && attendues.TrueForAll(l => new HashSet<string>(texte.Replace("\r", "").Split('\n')).Contains(l));
        static string Nom(Lieu lieu, long rang)
        {
            LieuPlace place = lieu.Lieux?.FirstOrDefault(p => p.Rang == rang);
            if (place?.Nom != null) return place.Nom;
            throw Echec(place?.AbsenceDuNom ?? lieu.AbsenceDesLieux ?? "nom absent du rang " + rang.ToString(CultureInfo.InvariantCulture));
        }
    }
}
