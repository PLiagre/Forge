using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Lot 890 : l'ordre de part de Mistra daté et en tonnes. `-forge890Tick` ajoute « · tick N » au message et rougit sur « mot interdit ».
    static class Lot890
    {
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause); static string Ligne(string t) => t == null ? "(aucun)" : t.Replace("\r", "").Replace("\n", " | ");
        [ScenarioDeCapture(890, "part-datee")]
        static IEnumerator PartDatee(Camera camera)
        {
            for (var e = Lot656.PartPosee(camera); e.MoveNext();) yield return null;
            var recu = Lot656.commandes?.Ordre.Recu; if (recu?.AppliqueeAuTick == null) throw Echec("le lot 656 n'a gardé ni commandes ni reçu accepté");
            string releve = (Lot656.Releve() ?? throw Echec("relevé absent")).text, message = Lot656.Message().text; // dans une même image
            if (Environment.GetCommandLineArgs().Contains("-forge890Tick")) message += " · tick " + recu.AppliqueeAuTick.Value.ToString(CultureInfo.InvariantCulture);
            if (!releve.StartsWith("Prélèvement : 25 % · relevé au jour", StringComparison.Ordinal)) throw Echec("relevé sans date : « " + Ligne(releve) + " »"); Propre(releve);
            if (!message.Contains("Ordre reçu au jour")) throw Echec("reçu sans date : « " + Ligne(message) + " »"); Propre(message);
            Debug.Log("CAPTURE_890 maison " + Lot656.maison + "\nCAPTURE_890 relevé « " + Ligne(releve) + " »\nCAPTURE_890 message « " + Ligne(message) + " »");
        }
        static void Propre(string texte)
        { if (TexteDuMonde.Interdit(texte) is string mot) throw Echec("mot interdit « " + mot + " » : « " + Ligne(texte) + " »"); if (TexteDuMonde.SansUnite(texte) is string nu) throw Echec("nombre sans unité « " + nu + " » : « " + Ligne(texte) + " »"); }
    }
}
