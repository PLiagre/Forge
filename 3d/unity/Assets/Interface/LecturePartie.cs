using System;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;

namespace Forge.Interface
{
    public sealed class LecturePartie
    {
        public Lecture<MondeAvecMaisonLu> Monde { get; private set; }
        public Lecture<MaisonLue> Maison { get; private set; }
        // Les comptes de la maison du joueur, lus au même passage que le monde ; leur tick dit s'ils sont du même jour.
        public Lecture<ComptesDeMaison> Comptes { get; private set; }
        // Le pays de la maison du joueur (ses jauges et ses points), lu au même passage ; son tick dit s'il est du même jour que le monde.
        public Lecture<PaysLu> Pays { get; private set; }
        // Le reste de `/pays` (lieux, vassaux, totaux, bâtiments), lu juste après le pays ; son tick dit s'il est du même jour que le monde.
        public Lecture<TerresDuPays> Terres { get; private set; }
        // Les gestes du pays de la maison du joueur (prix, effet, refus), lus juste après les terres ; leur tick dit s'ils sont du même jour que le monde.
        public Lecture<GestesDuPays> Gestes { get; private set; }
        // Les maisons que le joueur peut prendre (`/jouables`). Sans maison du joueur, relues à chaque jour servi ; avec une maison,
        // lues une fois pour elle : sa fiche dit le pays pris et la ville de sa capitale. Une lecture manquée se relit au passage suivant.
        public Lecture<JouablesLus> Jouables { get; private set; }
        // La fiche servie de la maison du joueur, ou null : aucune maison, ou jouables non lus.
        public FicheJouable Jouable
        {
            get
            {
                string id = Monde != null && Monde.Presente ? Monde.Donnees.MaisonDuJoueur : null;
                return id == null || Jouables == null || !Jouables.Presente ? null : Jouables.Donnees.Fiches.FirstOrDefault(f => f.Id == id);
            }
        }
        public RecuIntention Recu { get; private set; }
        public bool Occupee { get; private set; }
        readonly Func<Lecture<MondeAvecMaisonLu>> lireMonde;
        readonly Func<string, Lecture<MaisonLue>> lireMaison;
        readonly Func<Lecture<JouablesLus>> lireJouables;
        readonly Func<string, RecuIntention> choisir;
        readonly Func<string, Lecture<ComptesDeMaison>> lireComptes;
        readonly Func<string, Lecture<PaysLu>> lirePays;
        readonly Func<string, Lecture<TerresDuPays>> lireTerres;
        readonly Func<string, Lecture<GestesDuPays>> lireGestes;
        // Ce pour quoi les jouables gardés ont été lus : la maison du joueur, ou, sans maison, le tick du monde lu.
        string jouablesPour;
        public bool PeutChoisir => !Occupee && Monde != null && Monde.Presente
            && Monde.Donnees.MaisonDuJoueur == null && Jouables != null && Jouables.Presente && Recu?.Acceptee != true;

        public LecturePartie(Func<Lecture<MondeAvecMaisonLu>> monde, Func<string, Lecture<MaisonLue>> maison,
            Func<Lecture<JouablesLus>> jouables, Func<string, RecuIntention> choisir, Func<string, Lecture<ComptesDeMaison>> comptes = null,
            Func<string, Lecture<PaysLu>> pays = null, Func<string, Lecture<TerresDuPays>> terres = null, Func<string, Lecture<GestesDuPays>> gestes = null)
        {
            lireMonde = monde; lireMaison = maison; lireJouables = jouables; this.choisir = choisir; lireComptes = comptes; lirePays = pays; lireTerres = terres; lireGestes = gestes;
        }

        // Le choix part par l'identifiant de la maison : le monde ramène lui-même une seigneurie de départ à son chemin.
        public static string IntentionDeChoix(string maison) =>
            "{\"type\":\"choisir_depart\",\"maison\":\"" + maison.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"}";

        public static LecturePartie Locale(int port) => new LecturePartie(
            () => { using var c = new ClientMonde(port, TimeSpan.FromSeconds(10)); return c.LireAvecMaison(); },
            id => { using var c = new ClientMaison(port, TimeSpan.FromSeconds(10)); return c.Lire(id); },
            () => { using var c = new ClientJouables(port, ClientJouables.DelaiMinimal); return c.Lire(); },
            id => { using var c = new ClientIntention(port, TimeSpan.FromSeconds(10)); return c.Deposer(IntentionDeChoix(id)); },
            id => { using var c = new ClientMaison(port, TimeSpan.FromSeconds(10)); return c.LireComptes(id); },
            id => { using var c = new ClientPays(port, TimeSpan.FromSeconds(10)); return c.Lire(id); },
            id => { using var c = new ClientPays(port, TimeSpan.FromSeconds(10)); return c.LireTerres(id); },
            id => { using var c = new ClientPays(port, TimeSpan.FromSeconds(10)); return c.LireGestes(id); });

        public async Task Actualiser()
        {
            if (Occupee) return;
            Occupee = true;
            try
            {
                var gardes = Jouables; string pour = jouablesPour;
                var lu = await Task.Run(() => {
                    var monde = lireMonde();
                    var id = monde.Presente ? monde.Donnees.MaisonDuJoueur : null;
                    var maison = id != null ? lireMaison(id) : null;
                    var comptes = id != null && lireComptes != null ? lireComptes(id) : null;
                    var pays = id != null && lirePays != null ? lirePays(id) : null;
                    var terres = id != null && lireTerres != null ? lireTerres(id) : null;
                    var gestes = id != null && lireGestes != null ? lireGestes(id) : null;
                    string cle = !monde.Presente ? null : id != null ? "maison " + id : "jour " + monde.Donnees.Monde.Tick;
                    var jouables = cle == null ? null : cle == pour && gardes != null && gardes.Presente ? gardes : lireJouables();
                    return (monde, maison, comptes, pays, terres, gestes, jouables, cle);
                });
                Monde = lu.monde; Maison = lu.maison; Comptes = lu.comptes; Pays = lu.pays; Terres = lu.terres; Gestes = lu.gestes;
                Jouables = lu.jouables; jouablesPour = lu.jouables != null && lu.jouables.Presente ? lu.cle : null;
            }
            catch (Exception e)
            {
                Monde = Lecture<MondeAvecMaisonLu>.Absent("Lecture impossible : " + e.GetBaseException().Message);
                Maison = null; Comptes = null; Pays = null; Terres = null; Gestes = null; Jouables = null; jouablesPour = null;
            }
            finally { Occupee = false; }
        }

        public async Task Choisir(string maison)
        {
            if (!PeutChoisir || maison == null || !Jouables.Donnees.Fiches.Any(f => f.Id == maison)) return;
            Occupee = true;
            try { Recu = await Task.Run(() => choisir(maison)); }
            catch (Exception e) { Recu = RecuIntention.Absente("Envoi impossible : " + e.GetBaseException().Message); }
            finally { Occupee = false; }
        }
    }
}
