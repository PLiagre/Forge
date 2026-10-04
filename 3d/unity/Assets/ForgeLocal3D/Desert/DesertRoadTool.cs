using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Le geste du joueur (lot 263) : clic gauche pose un point sur le terrain, Entrée trace la
    // route, Échap annule. Le clic ne fait que convertir un point d'écran en point du terrain.
    // Lot 293 : la route n'est plus posée par l'outil. Il l'essaie sur le relief (DesertRoads.Poser
    // en essai, qui refuse la route trop raide), la dépose au monde comme intention `tracer_route`,
    // puis dessine au tick suivant les rues neuves que `/plan` publie. Toute route en chantier est
    // en terre battue. Le panneau est un texte posé devant la caméra : il apparaît aussi dans les
    // captures.
    public sealed class DesertRoadTool : MonoBehaviour
    {
        public DesertRoads roads;public Camera view;
        public const string Revetement="terre";public double largeur=4;
        // Piloté par le contrôle : ni souris ni clavier, et Attendre appelé par lui.
        public bool automatique;
        readonly List<(double x,double y)> points=new();
        public (double x,double y)[] Derniers{get;private set;}=new (double,double)[0];
        public string Message{get;private set;}="";
        // Le service du monde : la cellule lue sur la ligne de commande, le port du service local.
        public long Cellule{get;private set;}=-1;public int Port{get;private set;}=-1;
        // Le reçu du dernier dépôt ; null tant que rien n'est déposé.
        public RecuIntention Recu{get;private set;}
        // Les rues neuves du plan dessinées par Attendre : identifiant et résultat de la pose.
        public readonly List<(long identifiant,DesertRoads.Resultat resultat)> Posees=new();
        ClientIntention depot;ClientPlan plan;string erreurCellule;
        RecuIntention enAttente;HashSet<long> connues;double prochaineLecture;
        TextMesh panneau,halo;
        const string Aide="Clic : poser un point · Entrée : tracer la route · Échap : annuler";
        const double PeriodeLecture=.25;
        static readonly TimeSpan Delai=TimeSpan.FromSeconds(1);

        void Awake()
        {
            var font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            TextMesh Texte(string nom,Transform parent,Color couleur)
            {
                var go=new GameObject(nom);go.transform.SetParent(parent,false);
                var t=go.AddComponent<TextMesh>();t.font=font;go.GetComponent<MeshRenderer>().sharedMaterial=font.material;
                t.fontSize=64;t.anchor=TextAnchor.LowerLeft;t.color=couleur;return t;
            }
            panneau=Texte("Panneau des routes",view.transform,new Color(.12f,.06f,.03f));
            // Un halo clair derrière le texte : il reste lisible sur le sable comme dans l'ombre.
            halo=Texte("Halo",panneau.transform,new Color(1f,.95f,.84f,.9f));
            Cellule=PanneauLieu.LireCellule(Environment.GetCommandLineArgs(),PanneauLieu.CELLULE_PAR_DEFAUT,out erreurCellule);
            Port=PanneauLieu.DEFAULT_SERVICE_PORT;
            if(erreurCellule==null){depot=new ClientIntention(Port,Delai);plan=new ClientPlan(Port,Delai);}
            Afficher(erreurCellule??Aide);
        }
        void OnDestroy(){depot?.Dispose();plan?.Dispose();depot=null;plan=null;}
        void Afficher(string texte)
        {
            Message=texte;
            string etat="Terre battue, "+largeur.ToString("0.#")+" m"+(points.Count>0?" · "+points.Count+" point(s)":"");
            panneau.text=texte==Aide?etat+"\n"+Aide:texte+"\n"+etat;halo.text=panneau.text;
            Placer();
        }
        // En bas à gauche de l'image, à hauteur de lecture quelle que soit la focale.
        public void Placer()
        {
            if(!panneau)return;
            float d=view.nearClipPlane+.5f,h=2*d*Mathf.Tan(view.fieldOfView*Mathf.Deg2Rad/2),w=h*view.aspect;
            var t=panneau.transform;t.localRotation=Quaternion.identity;t.localScale=Vector3.one;panneau.characterSize=1;
            var r=panneau.GetComponent<MeshRenderer>();float lignes=Mathf.Max(1,panneau.text.Count(c=>c=='\n')+1);
            float ligne=r.localBounds.size.y/lignes;
            if(ligne>0)t.localScale=Vector3.one*(h/32/ligne);
            halo.transform.localPosition=new Vector3(ligne*.06f,-ligne*.06f,ligne*.05f);
            t.localPosition=new Vector3(-w/2+h*.03f,-h/2+h*.04f,d);
        }

        void Update()
        {
            if(automatique)return;
            if(enAttente!=null&&Time.realtimeSinceStartupAsDouble>=prochaineLecture)
            {prochaineLecture=Time.realtimeSinceStartupAsDouble+PeriodeLecture;Attendre();}
            var mouse=Mouse.current;var k=Keyboard.current;
            if(mouse!=null&&mouse.leftButton.wasPressedThisFrame)Clic(mouse.position.ReadValue());
            if(k==null)return;
            if(k.enterKey.wasPressedThisFrame||k.numpadEnterKey.wasPressedThisFrame)Valider();
            if(k.escapeKey.wasPressedThisFrame)Annuler();
        }
        void LateUpdate()=>Placer();

        public bool Clic(Vector2 ecran)
        {
            var ray=view.ScreenPointToRay(ecran);
            if(!roads.terrain.GetComponent<TerrainCollider>().Raycast(ray,out var hit,10000)){Afficher("Ce point n'est pas sur le terrain.");return false;}
            points.Add(roads.PointExact(hit.point));Afficher(Aide);return true;
        }
        public void Annuler(){points.Clear();Recu=null;Afficher(Aide);}

        // Essaie la route sur le relief, puis la dépose au monde. Le terrain ne bouge pas ici :
        // la route se dessine dans Attendre, d'après le plan du tick suivant. Rend le résultat de l'essai.
        public DesertRoads.Resultat Valider()
        {
            if(points.Count<2){Afficher("Il faut au moins deux points.");return null;}
            Recu=null;Posees.Clear();
            var g=new DesertRoads.Geste{id="joueur",revetement=Revetement,largeur=largeur,x=points.Select(p=>p.x).ToArray(),y=points.Select(p=>p.y).ToArray()};
            Derniers=points.ToArray();points.Clear();
            var r=roads.Poser(g,essai:true);
            // Une route que le relief refuse n'atteint jamais le monde.
            if(!r.acceptee){Afficher(r.message);return r;}
            if(erreurCellule!=null){Afficher(erreurCellule);return r;}
            var lu=plan.Lire(Cellule);
            if(!lu.Presente){Afficher("Pas de plan : "+lu.Absence);return r;}
            var avant=new HashSet<long>(lu.Plan.Rues.Select(u=>u.Identifiant));
            Recu=depot.Deposer(Intention(g));
            if(Recu.Acceptee)
            {
                // Un dépôt déjà en attente garde son relevé : ses rues neuves restent à dessiner.
                if(enAttente==null)connues=avant;
                enAttente=Recu;
                Afficher("Route déposée au monde : elle se trace au tick suivant (après le tick "+Recu.AppliqueeAuTick.Value.ToString(CultureInfo.InvariantCulture)+").");
            }
            else Afficher(Recu.Presente?"Le monde refuse la route : "+Recu.Erreur:"Pas de reçu : "+Recu.Absence);
            return r;
        }

        // Formée à la main : les nombres en culture invariante, au format "R" (aller-retour exact).
        string Intention(DesertRoads.Geste g)
        {
            string N(double v)=>v.ToString("R",CultureInfo.InvariantCulture);
            var s=new StringBuilder("{\"type\":\"tracer_route\",\"cell\":").Append(Cellule.ToString(CultureInfo.InvariantCulture)).Append(",\"points\":[");
            for(int i=0;i<g.x.Length;i++)s.Append(i>0?",":"").Append('[').Append(N(g.x[i])).Append(',').Append(N(g.y[i])).Append(']');
            return s.Append("],\"largeur_m\":").Append(N(g.largeur)).Append('}').ToString();
        }

        // Après le tick qui a appliqué le dépôt, dessine chaque rue apparue au plan depuis le dépôt,
        // de tout auteur, dans l'ordre du plan. Faux tant que ce tick n'est pas publié.
        public bool Attendre()
        {
            if(enAttente==null||plan==null)return false;
            var lu=plan.Lire(Cellule);
            if(!lu.Presente||lu.Plan.Tick<=enAttente.AppliqueeAuTick.Value)return false;
            DesertRoads.Resultat dernier=null;
            foreach(var rue in lu.Plan.Rues.Where(u=>!connues.Contains(u.Identifiant)))
            {
                dernier=roads.Poser(new DesertRoads.Geste{id="plan_"+rue.Identifiant.ToString(CultureInfo.InvariantCulture),revetement=Revetement,largeur=rue.LargeurM,
                    x=rue.Points.Select(p=>p.X).ToArray(),y=rue.Points.Select(p=>p.Y).ToArray()});
                Posees.Add((rue.Identifiant,dernier));
            }
            Afficher(dernier!=null?dernier.message:"Aucune rue neuve au plan après le tick "+lu.Plan.Tick.ToString(CultureInfo.InvariantCulture)+".");
            enAttente=null;connues=null;
            return true;
        }
    }
}
