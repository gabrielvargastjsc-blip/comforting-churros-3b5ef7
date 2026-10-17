import SwiftUI
import SwiftData

// Tela de um exercício: observação e a lista de séries, onde você registra
// carga, repetições, se fez, como foi (feedback) e uma nota por série.
struct ExercicioView: View {
    @Bindable var exercicio: Exercicio
    @Environment(\.modelContext) private var context

    private var seriesOrdenadas: [Serie] {
        exercicio.series.sorted { $0.ordem < $1.ordem }
    }

    var body: some View {
        Form {
            Section("Exercício") {
                TextField("Nome", text: $exercicio.nome)
                TextField("Grupo (ex: peito)", text: $exercicio.grupo)
                TextField("Observação", text: $exercicio.observacao, axis: .vertical)
            }
            Section("Séries") {
                ForEach(seriesOrdenadas) { serie in
                    SerieRow(serie: serie)
                }
                .onDelete(perform: apagarSerie)
                Button(action: adicionarSerie) {
                    Label("Adicionar série", systemImage: "plus")
                }
            }
        }
        .navigationTitle(exercicio.nome.isEmpty ? "Exercício" : exercicio.nome)
        .navigationBarTitleDisplayMode(.inline)
    }

    private func adicionarSerie() {
        let ultima = seriesOrdenadas.last
        let nova = Serie(ordem: (ultima?.ordem ?? 0) + 1,
                         cargaKg: ultima?.cargaKg ?? 0,
                         repeticoes: ultima?.repeticoes ?? 10)
        nova.exercicio = exercicio
        exercicio.series.append(nova)
        context.insert(nova)
    }

    private func apagarSerie(_ offsets: IndexSet) {
        let lista = seriesOrdenadas
        for i in offsets { context.delete(lista[i]) }
    }
}

// Uma linha de série, editável.
struct SerieRow: View {
    @Bindable var serie: Serie
    private let feedbacks = ["fácil", "médio", "difícil"]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Série \(serie.ordem)").font(.subheadline).bold()
                Spacer()
                Toggle("Feita", isOn: $serie.feita).labelsHidden()
            }
            HStack(spacing: 16) {
                HStack {
                    Text("Carga")
                    TextField("kg", value: $serie.cargaKg, format: .number)
                        .keyboardType(.decimalPad)
                        .multilineTextAlignment(.trailing)
                }
                HStack {
                    Text("Reps")
                    TextField("reps", value: $serie.repeticoes, format: .number)
                        .keyboardType(.numberPad)
                        .multilineTextAlignment(.trailing)
                }
            }
            Picker("Como foi", selection: $serie.feedback) {
                ForEach(feedbacks, id: \.self) { Text($0).tag($0) }
            }
            .pickerStyle(.segmented)
            TextField("Observação da série", text: $serie.nota, axis: .vertical)
        }
        .padding(.vertical, 4)
    }
}
