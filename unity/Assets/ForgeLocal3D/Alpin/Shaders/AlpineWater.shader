Shader "Forge/AlpineWater"
{
    Properties { _BaseMap("Eau",2D)="white"{} _BaseColor("Teinte",Color)=(1,1,1,1) }
    SubShader
    {
        Tags {"RenderPipeline"="UniversalPipeline" "RenderType"="Opaque" "Queue"="Geometry+20"}
        Cull Off
        Pass
        {
            Tags {"LightMode"="UniversalForward"}
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            float _AlpineWind,_AlpineDaylight;
            float4 _AlpineAmbient;
            float hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
            float noise(float2 p){float2 a=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(hash(a),hash(a+float2(1,0)),f.x),lerp(hash(a+float2(0,1)),hash(a+1),f.x),f.y);}
            struct A {float4 position:POSITION;float2 uv:TEXCOORD0;};
            struct V {float4 position:SV_POSITION;float3 world:TEXCOORD0;float2 uv:TEXCOORD1;float fog:TEXCOORD2;};
            V Vert(A a){V o;o.world=TransformObjectToWorld(a.position.xyz);o.position=TransformWorldToHClip(o.world);o.uv=a.uv;o.fog=ComputeFogFactor(o.position.z);return o;}
            half4 Frag(V i):SV_Target
            {
                float t=_Time.y;float2 flow=float2(i.world.x*.7,i.world.z*.65+t*.65);
                float turbulence=noise(flow)*.7+noise(flow*2.4)*.3;
                float wave=sin(i.world.z*3.8+t*4.1+turbulence*9);
                float3 n=normalize(float3(cos(i.world.x*2.6+t+turbulence)*.08,1,sin(i.world.z*1.7+t*1.7)*.12));
                Light l=GetMainLight(TransformWorldToShadowCoord(i.world));
                float3 v=normalize(GetWorldSpaceViewDir(i.world));float fres=pow(1-saturate(dot(n,v)),3);
                float edge=pow(saturate(abs(i.uv.x-.5)*2),9);
                float foam=smoothstep(.93,1,wave)*smoothstep(.50,.80,turbulence)*(.24+edge*.55);
                float3 color=lerp(float3(.025,.17,.16),float3(.22,.38,.43),fres*.65+edge*.35);
                color=lerp(color,float3(.63,.72,.69),foam);
                color*=_AlpineAmbient.rgb+l.color*(.35+.4*saturate(dot(n,l.direction)))*lerp(.5,1,l.shadowAttenuation);
                color+=l.color*pow(saturate(dot(n,normalize(v+l.direction))),100)*.12;
                color*=1-_AlpineDaylight*.45;
                return half4(MixFog(color,i.fog),1);
            }
            ENDHLSL
        }
    }
}
