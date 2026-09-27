using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;

namespace ForgeLocal3D
{
    // Le geste du joueur (lot 263) : clic gauche pose un point sur le terrain, Entrée trace la
    // route, Échap annule, T change de revêtement. Le clic ne fait que convertir un point
    // d'écran en point du terrain ; la route passe par DesertRoads.Poser, la même entrée que le
    // jeu de gestes du contrôle. Le panneau est un texte posé devant la caméra : il apparaît
    // aussi dans les captures.
    public sealed class DesertRoadTool : MonoBehaviour
    {
        public DesertRoads roads;public Camera view;
        public string revetement="terre";public double largeur=4;
        // Piloté par le contrôle : ni souris ni clavier.
        public bool automatique;
        readonly List<(double x,double y)> points=new();
        public (double x,double y)[] Derniers{get;private set;}=new (double,double)[0];
        public string Message{get;private set;}="";
        TextMesh panneau,halo;
        const string Aide="Clic : poser un point · Entrée : tracer la route · Échap : annuler · T : terre battue / pavés";

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
            Afficher(Aide);
        }
        void Afficher(string texte)
        {
            Message=texte;
            string etat=(revetement=="paves"?"Pavés":"Terre battue")+", "+largeur.ToString("0.#")+" m"+(points.Count>0?" · "+points.Count+" point(s)":"");
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
            var mouse=Mouse.current;var k=Keyboard.current;
            if(mouse!=null&&mouse.leftButton.wasPressedThisFrame)Clic(mouse.position.ReadValue());
            if(k==null)return;
            if(k.enterKey.wasPressedThisFrame||k.numpadEnterKey.wasPressedThisFrame)Valider();
            if(k.escapeKey.wasPressedThisFrame)Annuler();
            if(k.tKey.wasPressedThisFrame){revetement=revetement=="paves"?"terre":"paves";Afficher(Aide);}
        }
        void LateUpdate()=>Placer();

        public bool Clic(Vector2 ecran)
        {
            var ray=view.ScreenPointToRay(ecran);
            if(!roads.terrain.GetComponent<TerrainCollider>().Raycast(ray,out var hit,10000)){Afficher("Ce point n'est pas sur le terrain.");return false;}
            points.Add(roads.PointExact(hit.point));Afficher(Aide);return true;
        }
        public void Annuler(){points.Clear();Afficher(Aide);}
        public DesertRoads.Resultat Valider()
        {
            if(points.Count<2){Afficher("Il faut au moins deux points.");return null;}
            var g=new DesertRoads.Geste{id="joueur",revetement=revetement,largeur=largeur,x=points.Select(p=>p.x).ToArray(),y=points.Select(p=>p.y).ToArray()};
            Derniers=points.ToArray();points.Clear();
            var r=roads.Poser(g);Afficher(r.message);return r;
        }
    }
}
