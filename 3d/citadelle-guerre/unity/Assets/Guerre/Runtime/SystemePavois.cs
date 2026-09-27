using Unity.Burst;
using Unity.Collections;
using Unity.Entities;
using Unity.Mathematics;
using Unity.Transforms;

namespace Guerre
{
    // Chaque pavois suit son porteur : planté devant lui quand il s'arrête pour tirer, porté dans
    // son dos quand il marche. Si le porteur tombe, le pavois reste où il était ; s'il le portait
    // sur le dos, il tombe à plat avec lui.
    [BurstCompile]
    [UpdateInGroup(typeof(SimulationSystemGroup))]
    [UpdateAfter(typeof(SystemePilotage))]
    [UpdateBefore(typeof(TransformSystemGroup))]
    public partial struct SystemePavois : ISystem
    {
        ComponentLookup<Soldat> soldats;

        public void OnCreate(ref SystemState state)
        {
            soldats = state.GetComponentLookup<Soldat>(true);
            state.RequireForUpdate<Pavois>();
        }

        [BurstCompile]
        public void OnUpdate(ref SystemState state)
        {
            soldats.Update(ref state);
            state.Dependency = new Suivre { Soldats = soldats }.ScheduleParallel(state.Dependency);
        }

        [BurstCompile]
        partial struct Suivre : IJobEntity
        {
            [ReadOnly] public ComponentLookup<Soldat> Soldats;

            // Un pavois planté est un objet posé : il reste où il est quand son porteur fait un pas
            // ou tombe. Arrêté, on le replante devant soi dès qu'il n'y est plus (à 30 cm près) ;
            // en marche, on ne le reprend que si l'on s'en éloigne.
            void Execute(ref Pavois p, ref LocalTransform t)
            {
                if (!Soldats.HasComponent(p.Porteur))
                {
                    if (p.Plante == 0 && p.Tombe == 0)
                    {
                        p.Tombe = 1;
                        t.Position.y -= 0.3f;
                        t.Rotation = math.mul(t.Rotation, quaternion.RotateX(math.PI / 2));
                    }
                    return;
                }
                var s = Soldats[p.Porteur];
                float3 regard = new float3(s.Regard.x, 0, s.Regard.y);
                if (math.lengthsq(regard) < 1e-4f) regard = new float3(0, 0, 1);
                float3 ici = s.Lieu + regard * Armes.PavoisDistance;
                if (s.Poste != 0 && (p.Plante == 0 || math.distance(ici.xz, p.Base.xz) > 0.3f))
                {
                    p.Plante = 1; p.Base = ici; p.Normale = s.Regard;
                }
                else if (p.Plante != 0 && s.Poste == 0 && math.distance(s.Lieu.xz, p.Base.xz) > 1.5f) p.Plante = 0;

                if (p.Plante != 0)
                    t = LocalTransform.FromPositionRotation(p.Base, quaternion.LookRotationSafe(new float3(p.Normale.x, 0, p.Normale.y), math.up()));
                else
                    t = LocalTransform.FromPositionRotation(s.Lieu - regard * 0.24f + new float3(0, 0.3f, 0),
                        math.mul(quaternion.LookRotationSafe(regard, math.up()), quaternion.RotateX(-0.12f)));
            }
        }
    }
}
