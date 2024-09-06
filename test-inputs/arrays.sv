module vector_operations(
    input logic [5:0] vector1, vector2,vector3,
    input logic a,b,
    output logic [5:0] prova1,prova2,prova3,prova4,
    output logic prova5
);

    // Assegnazione di valori ai vettori e allo scalare        
   // Operazione AND elemento per elemento tra i vettori
   assign prova1 = vector3 | (vector1 & vector2);
   assign prova2 = vector1 | vector2;
   assign prova3 = vector1 ^ vector2; 
   assign prova4 = ~ vector1;
   assign prova5 = a & b;
endmodule
