function I_model=sir_simulate(params,t,N,I0)
%params=[beta,gamma,a]
beta=params(1);
gamma=params(2);
a=params(3);
S0=N-I0;
y0=[S0;I0;0];
[~,y]=ode45(@(t,y)sir_ode(t,y,beta,gamma),t,y0);
I_sim=y(:,2);
I_model=a*I_sim/N;
end