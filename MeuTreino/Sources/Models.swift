import Foundation
import SwiftData

// Modelo de dados do seu app, espelhando o que você faz no Prime App:
// registrar treinos, com exercícios, séries, carga, repetições, feedback e observações.

@Model
final class Treino {
    var nome: String
    var data: Date
    var concluido: Bool
    @Relationship(deleteRule: .cascade, inverse: \Exercicio.treino)
    var exercicios: [Exercicio]

    init(nome: String, data: Date = .now, concluido: Bool = false) {
        self.nome = nome
        self.data = data
        self.concluido = concluido
        self.exercicios = []
    }
}

@Model
final class Exercicio {
    var nome: String
    var grupo: String
    var ordem: Int
    var observacao: String
    var treino: Treino?
    @Relationship(deleteRule: .cascade, inverse: \Serie.exercicio)
    var series: [Serie]

    init(nome: String, grupo: String = "", ordem: Int = 0, observacao: String = "") {
        self.nome = nome
        self.grupo = grupo
        self.ordem = ordem
        self.observacao = observacao
        self.series = []
    }
}

@Model
final class Serie {
    var ordem: Int
    var cargaKg: Double
    var repeticoes: Int
    var feita: Bool
    var feedback: String   // "fácil", "médio", "difícil"
    var nota: String
    var exercicio: Exercicio?

    init(ordem: Int, cargaKg: Double = 0, repeticoes: Int = 0,
         feita: Bool = false, feedback: String = "médio", nota: String = "") {
        self.ordem = ordem
        self.cargaKg = cargaKg
        self.repeticoes = repeticoes
        self.feita = feita
        self.feedback = feedback
        self.nota = nota
    }
}

@Model
final class Nota {
    var data: Date
    var texto: String

    init(data: Date = .now, texto: String = "") {
        self.data = data
        self.texto = texto
    }
}
