function dydt=sir_ode(~,y,beta,gamma)
S=y(1);
I=y(2);
R=y(3);
N=S+I+R;
dS=-beta * S * I / N;
dI=beta * S * I / N - gamma * I;
dR=gamma * I;
dydt=[dS;dI;dR];
end