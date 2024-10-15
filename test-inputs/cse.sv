module CseTransformation(input logic a, b,c,
                output logic out1,out2);

    assign out1 = a & b;
    assign out2 = (a & b) ^ (a & b);
    // questo produce alla fine un ccnot controllato dallo stesso qubit due volte
    // non penso sia fattibile bisognerebbe implementare un passaggio che se nota questa CseTransformation
    // lo sostituisce con il gate equivalente
endmodule