function [params_est,resnorm]=fit_sir_quiet(t,I_obs,params0,lb,ub,N,I0_obs,options)
fitfun=@(params,tt) sir_simulate(params,tt,N,I0_obs);
[params_est,resnorm]=lsqcurvefit(fitfun,params0,t,I_obs,lb,ub,options);
end